from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db import models
from django.conf import settings
import os
import shutil
import uuid
import io

from .models import LibraryFile, FileCategory
from .forms import LibraryFileForm, FileCategoryForm
from Orgnization.models import Employee

# Chunked upload settings
CHUNK_SIZE = 5 * 1024 * 1024          # 5MB
MAX_FILE_SIZE = 100 * 1024 * 1024     # 100MB


def _user_role(request):
    emp = getattr(request.user, 'employee', None)
    if emp is None:
        try:
            emp = Employee.objects.filter(user=request.user).first()
        except Exception:
            emp = None
    role = emp.role if emp else None
    return role


def _can_upload(request):
    return _user_role(request) in ('admin', 'manager')


def _can_manage(request):
    return _user_role(request) == 'admin'


@login_required
def file_library_list(request):
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')

    files = LibraryFile.objects.select_related('category', 'uploaded_by')
    if q:
        files = files.filter(title__icontains=q)
    if category_id:
        files = files.filter(category_id=category_id)

    categories = FileCategory.objects.annotate(
        file_count=models.Count('files')
    )

    # Incomplete transcode videos (PENDING / PROCESSING / FAILED)
    video_expr = models.Q()
    for ext in LibraryFile.VIDEO_EXTS:
        video_expr |= models.Q(file__endswith='.' + ext)
    pending_videos = LibraryFile.objects.filter(video_expr).exclude(video_status='COMPLETED')

    context = {
        'files': files,
        'categories': categories,
        'q': q,
        'selected_category': category_id,
        'can_upload': _can_upload(request),
        'can_manage': _can_manage(request),
        'total_size': sum(f.file.size for f in files if f.file and f.file.size),
        'pending_videos': pending_videos,
    }
    return render(request, 'filelibrary/file_library_list.html', context)


@login_required
@require_POST
def retry_transcode(request, pk=None):
    """Re-trigger transcoding for incomplete videos (can specify single or all incomplete)"""
    if not _can_manage(request):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('filelibrary:file-library-list')

    video_expr = models.Q()
    for ext in LibraryFile.VIDEO_EXTS:
        video_expr |= models.Q(file__endswith='.' + ext)
    qs = LibraryFile.objects.filter(video_expr).exclude(video_status='COMPLETED')

    if pk:
        qs = qs.filter(pk=pk)
        target = get_object_or_404(LibraryFile, pk=pk)
        if not target.is_video:
            messages.error(request, 'This file is not a video.')
            return redirect('filelibrary:file-library-list')
        if target.video_status == 'COMPLETED':
            messages.info(request, f'"{target.title}" transcoding completed, no retry needed.')
            return redirect('filelibrary:file-library-list')

    count = qs.count()
    if count == 0:
        messages.info(request, 'No videos require transcoding.')
        return redirect('filelibrary:file-library-list')

    for f in qs:
        f.video_status = 'PENDING'
        f.video_error = ''
        f.save(update_fields=['video_status', 'video_error'])
        from .video import transcode_video
        transcode_video(f.pk)  # Trigger background transcoding

    target_name = qs.first().title if pk else ''
    suffix = f' ({target_name})' if pk else ''
    messages.success(request, f'Restarted transcoding for {count} video(s){suffix}. Please check status later.')
    return redirect('filelibrary:file-library-list')


@login_required
def file_upload(request):
    if not _can_upload(request):
        messages.error(request, 'You do not have permission to upload files.')
        return redirect('filelibrary:file-library-list')

    if request.method == 'POST':
        form = LibraryFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.save(commit=False)
            f.uploaded_by = request.user
            f.save()
            # Video: background standardized transcoding (720p / H.264 / MP4)
            if f.is_video:
                f.video_status = 'PENDING'
                f.save(update_fields=['video_status'])
                from .video import transcode_video
                transcode_video(f.pk)
                messages.success(request, f'File "{f.title}" uploaded. Video is transcoding in background (720p/H.264).')
            else:
                messages.success(request, f'File "{f.title}" uploaded.')
            return redirect('filelibrary:file-library-list')
    else:
        form = LibraryFileForm()
    return render(request, 'filelibrary/file_upload.html', {
        'form': form,
        'chunk_size': CHUNK_SIZE,
        'max_file_size': MAX_FILE_SIZE,
    })


# ── Chunked Upload (Chunk) ──────────────────────────────────────────────────

def _chunk_dir(upload_id):
    """Chunk temporary directory: media/chunk_tmp/<upload_id>/"""
    return os.path.join(settings.MEDIA_ROOT, 'chunk_tmp', str(upload_id))


def _cleanup_chunk_dir(upload_id):
    d = _chunk_dir(upload_id)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


@login_required
def chunk_status(request):
    """Query received chunk indices (supports resumable upload)"""
    if not _can_upload(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    upload_id = request.GET.get('upload_id', '')
    if not upload_id:
        return JsonResponse({'success': False, 'error': 'Missing upload_id.'}, status=400)
    d = _chunk_dir(upload_id)
    received = []
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.startswith('chunk_'):
                try:
                    received.append(int(fn.replace('chunk_', '')))
                except ValueError:
                    pass
    return JsonResponse({'success': True, 'received': sorted(received)})


@login_required
@require_POST
def chunk_upload(request):
    """Receive a chunk; merge into complete file when last chunk arrives"""
    if not _can_upload(request):
        return JsonResponse({'success': False, 'error': 'You do not have permission to upload files.'}, status=403)

    upload_id = request.POST.get('upload_id', '').strip()
    chunk_index = request.POST.get('chunk_index')
    total_chunks = request.POST.get('total_chunks')
    filename = request.POST.get('filename', '').strip()
    total_size = request.POST.get('total_size', '')
    chunk_file = request.FILES.get('chunk')

    # Parameter validation
    try:
        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)
        total_size = int(total_size)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid chunk parameter format.'}, status=400)

    if not upload_id or not filename or not chunk_file:
        return JsonResponse({'success': False, 'error': 'Missing required parameters.'}, status=400)
    if chunk_index < 0 or chunk_index >= total_chunks:
        return JsonResponse({'success': False, 'error': 'Invalid chunk index.'}, status=400)
    if total_size > MAX_FILE_SIZE:
        return JsonResponse({'success': False, 'error': f'File exceeds {MAX_FILE_SIZE // 1024 // 1024}MB limit.'}, status=400)

    # Check upload_id validity (UUID format only to prevent path traversal)
    try:
        uuid.UUID(upload_id)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid upload_id.'}, status=400)

    # Save chunk
    d = _chunk_dir(upload_id)
    os.makedirs(d, exist_ok=True)
    chunk_path = os.path.join(d, f'chunk_{chunk_index}')
    with open(chunk_path, 'wb+') as dest:
        for c in chunk_file.chunks():
            dest.write(c)

    # If not all arrived, report current progress
    received = sorted(int(fn.replace('chunk_', '')) for fn in os.listdir(d) if fn.startswith('chunk_'))
    if len(received) < total_chunks:
        return JsonResponse({
            'success': True,
            'received': received,
            'done': False,
        })

    # All arrived -> Merge
    merged_path = os.path.join(d, 'merged.bin')
    try:
        with open(merged_path, 'wb') as out:
            for i in range(total_chunks):
                p = os.path.join(d, f'chunk_{i}')
                if not os.path.isfile(p):
                    raise FileNotFoundError(f'Missing chunk {i}')
                with open(p, 'rb') as src:
                    shutil.copyfileobj(src, out)
        merged_size = os.path.getsize(merged_path)
        if merged_size != total_size:
            raise ValueError(f'Merged size mismatch: {merged_size} != {total_size}')
        if merged_size > MAX_FILE_SIZE:
            raise ValueError('Merged file exceeds size limit')
    except Exception as e:
        _cleanup_chunk_dir(upload_id)
        return JsonResponse({'success': False, 'error': f'Merge failed: {e}'}, status=500)

    # Create LibraryFile and move to formal directory
    title = request.POST.get('title', '').strip() or os.path.splitext(filename)[0]
    category_id = request.POST.get('category', '')
    description = request.POST.get('description', '').strip()

    # Move file using FileSystemStorage
    from django.core.files.base import File
    from django.core.files.storage import default_storage
    target_name = os.path.join('file_library', filename)
    target_path = default_storage.path(target_name)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.move(merged_path, target_path)
    _cleanup_chunk_dir(upload_id)

    lib_file = LibraryFile(
        title=title,
        description=description or None,
        uploaded_by=request.user,
    )
    if category_id:
        try:
            lib_file.category = FileCategory.objects.get(pk=int(category_id))
        except (ValueError, FileCategory.DoesNotExist):
            lib_file.category = None
    lib_file.file.name = target_name
    lib_file.save()

    # Video: background standardized transcoding (720p / H.264 / MP4)
    if lib_file.is_video:
        lib_file.video_status = 'PENDING'
        lib_file.save(update_fields=['video_status'])
        from .video import transcode_video
        transcode_video(lib_file.pk)

    return JsonResponse({
        'success': True,
        'done': True,
        'file_id': lib_file.pk,
        'title': lib_file.title,
        'video_transcoding': lib_file.is_video,
    })


@login_required
def file_edit(request, pk):
    if not _can_manage(request):
        messages.error(request, 'Only system administrators can edit files.')
        return redirect('filelibrary:file-library-list')

    f = get_object_or_404(LibraryFile, pk=pk)
    if request.method == 'POST':
        form = LibraryFileForm(request.POST, request.FILES, instance=f)
        if form.is_valid():
            form.save()
            messages.success(request, f'File "{f.title}" has been updated.')
            return redirect('filelibrary:file-library-list')
    else:
        form = LibraryFileForm(instance=f)
    return render(request, 'filelibrary/file_upload.html', {'form': form, 'editing': True, 'file_obj': f})


@login_required
@require_POST
def file_delete(request, pk):
    if not _can_manage(request):
        messages.error(request, 'Only system administrators can delete files.')
        return redirect('filelibrary:file-library-list')

    f = get_object_or_404(LibraryFile, pk=pk)
    title = f.title
    for field in ('file', 'video_standard'):
        file_obj = getattr(f, field, None)
        if file_obj:
            try:
                if os.path.isfile(file_obj.path):
                    os.remove(file_obj.path)
            except (OSError, ValueError):
                pass
    f.delete()
    messages.success(request, f'File "{title}" has been deleted.')
    return redirect('filelibrary:file-library-list')


@login_required
def file_download(request, pk):
    f = get_object_or_404(LibraryFile, pk=pk)
    if not f.file:
        raise Http404('File does not exist')
    try:
        if not os.path.isfile(f.file.path):
            raise Http404('File does not exist')
    except (OSError, ValueError):
        raise Http404('File could not be read')
    # Use X-Accel-Redirect to hand off to nginx directly
    response = HttpResponse()
    response['X-Accel-Redirect'] = f'/internal_media/{f.file.name}'
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = f'attachment; filename="{f.filename}"'
    return response


@login_required
def file_standard_download(request, pk):
    """Standardized video version is for online streaming only (720p/H.264/MP4), not available for download"""
    f = get_object_or_404(LibraryFile, pk=pk)
    if not f.is_video or not f.video_standard or f.video_status != 'COMPLETED':
        raise Http404('Standardized version not yet completed')
    try:
        if not os.path.isfile(f.video_standard.path):
            raise Http404('Standardized file does not exist')
    except (OSError, ValueError):
        raise Http404('File could not be read')
    # Always inline playback via X-Accel-Redirect
    response = HttpResponse()
    response['X-Accel-Redirect'] = f'/internal_media/{f.video_standard.name}'
    response['Content-Type'] = 'video/mp4'
    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline'
    return response


@login_required
def file_video_play(request, pk):
    """Video playback page (new tab): Dark player, streaming compressed standard version (720p/H.264)"""
    f = get_object_or_404(LibraryFile, pk=pk)
    if not f.is_video:
        raise Http404('This file is not a video')
    if f.video_status != 'COMPLETED' or not f.video_standard:
        # Transcoding not completed: show status hint
        return render(request, 'filelibrary/video_play.html', {
            'f': f,
            'not_ready': True,
        })
    return render(request, 'filelibrary/video_play.html', {
        'f': f,
        'not_ready': False,
    })


# ── Image Preview (Backend compression <100KB) ──────────────────────────────

PREVIEW_MAX_BYTES = 100 * 1024
PREVIEW_MAX_DIM = 1200
PREVIEW_QUALITY_START = 85


@login_required
def file_preview(request, pk):
    """Image formats: Pillow compresses <100KB then returns JPEG (SVG returns raw file)"""
    f = get_object_or_404(LibraryFile, pk=pk)
    if not f.file or not f.is_image:
        raise Http404('This file is not a previewable image')

    try:
        path = f.file.path
    except (OSError, ValueError):
        raise Http404('File could not be read')

    if not os.path.isfile(path):
        raise Http404('File does not exist')

    ext = os.path.splitext(f.filename)[1].lower()
    # SVG: Vector format, return raw file
    if ext == '.svg':
        try:
            with open(path, 'rb') as fh:
                return HttpResponse(fh.read(), content_type='image/svg+xml')
        except OSError:
            raise Http404('File could not be read')

    # Other formats: Pillow open -> scale -> quality stepped compression <100KB
    from PIL import Image, UnidentifiedImageError
    try:
        img = Image.open(path)
        img.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise Http404('Image could not be parsed')

    # Multi-frame format (GIF) take first frame; normalize to RGB
    try:
        img.seek(0)
    except Exception:
        pass
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    def _encode(w, h, q):
        out = img.copy()
        if (w, h) != img.size:
            out.thumbnail((w, h), Image.Resampling.LANCZOS)
        b = io.BytesIO()
        out.save(b, 'JPEG', quality=q, optimize=True)
        return b

    # Phase 1: Fixed dimensions, quality 85 -> 75 -> ... -> 20
    for quality in range(PREVIEW_QUALITY_START, 19, -10):
        buf = _encode(PREVIEW_MAX_DIM, PREVIEW_MAX_DIM, quality)
        if buf.tell() <= PREVIEW_MAX_BYTES:
            buf.seek(0)
            return HttpResponse(buf.getvalue(), content_type='image/jpeg')

    # Phase 2: If quality floor still exceeds limit -> downscale dimensions (800 -> 500 -> 300) then adjust quality
    for dim in (800, 500, 300):
        for quality in (60, 40, 25):
            buf = _encode(dim, dim, quality)
            if buf.tell() <= PREVIEW_MAX_BYTES:
                buf.seek(0)
                return HttpResponse(buf.getvalue(), content_type='image/jpeg')

    # Minimal: 300px / q=20
    buf = _encode(300, 300, 20)
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type='image/jpeg')


# ── Category Management (Admin only) ────────────────────────────────────────

@login_required
def category_create_ajax(request):
    """Built-in category creation endpoint for upload form (available to admin/manager)"""
    if not _can_upload(request):
        return JsonResponse({'success': False, 'error': 'You do not have permission to add categories.'}, status=403)
    if request.method == 'POST':
        form = FileCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            return JsonResponse({
                'success': True,
                'id': cat.pk,
                'name': cat.name,
            })
        return JsonResponse({'success': False, 'error': form.errors.as_text()}, status=400)
    return JsonResponse({'success': False, 'error': 'Only POST method is supported.'}, status=405)


@login_required
def category_list(request):
    if not _can_manage(request):
        messages.error(request, 'Only system administrators can manage categories.')
        return redirect('filelibrary:file-library-list')
    categories = FileCategory.objects.annotate(file_count=models.Count('files'))
    return render(request, 'filelibrary/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    if not _can_manage(request):
        messages.error(request, 'Only system administrators can add categories.')
        return redirect('filelibrary:file-library-list')
    if request.method == 'POST':
        form = FileCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category has been created.')
            return redirect('filelibrary:file-category-list')
    else:
        form = FileCategoryForm()
    return render(request, 'filelibrary/category_form.html', {'form': form, 'action': 'Create'})


@login_required
def category_edit(request, pk):
    if not _can_manage(request):
        messages.error(request, 'Only system administrators can edit categories.')
        return redirect('filelibrary:file-library-list')
    category = get_object_or_404(FileCategory, pk=pk)
    if request.method == 'POST':
        form = FileCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category has been updated.')
            return redirect('filelibrary:file-category-list')
    else:
        form = FileCategoryForm(instance=category)
    return render(request, 'filelibrary/category_form.html', {'form': form, 'action': 'Edit', 'category': category})


@login_required
@require_POST
def category_delete(request, pk):
    if not _can_manage(request):
        messages.error(request, 'Only system administrators can delete categories.')
        return redirect('filelibrary:file-library-list')
    category = get_object_or_404(FileCategory, pk=pk)
    if category.files.exists():
        messages.error(request, f'Category "{category.name}" still contains files and cannot be deleted.')
    else:
        category.delete()
        messages.success(request, f'Category "{category.name}" has been deleted.')
    return redirect('filelibrary:file-category-list')
