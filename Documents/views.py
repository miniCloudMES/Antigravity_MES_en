from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import PermissionDenied

from .models import DocumentCategory, Document, DocumentImage, DocumentAuditLog
from .forms import CategoryForm, DocumentForm, DocumentSubmitForm
from Orgnization.models import Employee

import base64
import uuid
import io
import re


def role_required(*roles):
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            employee = getattr(request.user, 'employee', None)
            if not employee or employee.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def log_audit(document, action, user, previous_status=None, new_status=None, notes=''):
    return DocumentAuditLog.objects.create(
        document=document,
        action=action,
        performed_by=user,
        previous_status=previous_status,
        new_status=new_status,
        notes=notes.strip() if notes else ''
    )


def save_document_images(request, document):
    """Process and save multiple document images and their descriptions"""
    # 1. Handle edits and deletions of existing images
    delete_ids = request.POST.getlist('delete_images')
    for img_id in delete_ids:
        try:
            img = DocumentImage.objects.get(id=img_id, document=document)
            img.delete()
        except DocumentImage.DoesNotExist:
            pass
        
    existing_ids = request.POST.getlist('existing_image_ids')
    for img_id in existing_ids:
        if img_id not in delete_ids:
            try:
                img = DocumentImage.objects.get(id=img_id, document=document)
                desc = request.POST.get(f'existing_image_desc_{img_id}', '').strip()
                if img.description != desc:
                    img.description = desc
                    img.save()
            except DocumentImage.DoesNotExist:
                pass

    # 2. Handle newly cropped images
    new_images_cropped = request.POST.getlist('new_images_cropped')
    new_images_descriptions = request.POST.getlist('new_images_descriptions')
    
    for i, b64 in enumerate(new_images_cropped):
        if b64.strip():
            if ',' in b64:
                b64 = b64.split(',', 1)[1]
            img_bytes = base64.b64decode(b64)
            file_obj = InMemoryUploadedFile(
                file=io.BytesIO(img_bytes),
                field_name='image',
                name=f"{uuid.uuid4().hex}.jpg",
                content_type='image/jpeg',
                size=len(img_bytes),
                charset=None,
            )
            
            desc = ""
            if i < len(new_images_descriptions):
                desc = new_images_descriptions[i].strip()
                
            DocumentImage.objects.create(
                document=document,
                image=file_obj,
                description=desc
            )

@login_required
def documents_dashboard(request):
    category_id = request.GET.get('category')
    status_filter = request.GET.get('status')
    categories = DocumentCategory.objects.all()
    pending_count = Document.objects.filter(status=Document.STATUS_PENDING).count()
    
    if category_id:
        selected_category = get_object_or_404(DocumentCategory, id=category_id)
        documents = Document.objects.filter(category=selected_category)
    elif status_filter == 'pending':
        selected_category = None
        documents = Document.objects.filter(status=Document.STATUS_PENDING)
    else:
        selected_category = None
        documents = Document.objects.all()
        
    context = {
        'documents': documents,
        'categories': categories,
        'selected_category': selected_category,
        'pending_count': pending_count,
        'status_filter': status_filter,
    }
    return render(request, 'documents/dashboard.html', context)

@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk)
    return render(request, 'documents/document_detail.html', {'document': document})

@login_required
def document_create(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST)
        if form.is_valid():
            document = form.save(commit=False)
            document.created_by = request.user
            document.save()
            save_document_images(request, document)
            log_audit(document, 'create', request.user, previous_status=None, new_status=document.status)
            messages.success(request, f"Document \"{document.title}\" was created successfully.")
            return redirect('document-detail', pk=document.pk)
    else:
        form = DocumentForm()
        # Pre-select category if passed in GET parameter
        category_id = request.GET.get('category')
        if category_id:
            form.fields['category'].initial = category_id
            
    return render(request, 'documents/document_form.html', {'form': form, 'document': None, 'action': 'Create'})

@login_required
def document_edit(request, pk):
    document = get_object_or_404(Document, pk=pk)
    user = request.user
    employee = getattr(user, 'employee', None)
    is_manager = employee and employee.role in ['admin', 'manager']
    is_submitter = document.submitted_by_id == user.id

    if document.status == Document.STATUS_PENDING:
        messages.warning(request, 'A document that is pending review cannot be edited.')
        return redirect('document-detail', pk=document.pk)

    if document.status in [Document.STATUS_DRAFT, Document.STATUS_REJECTED]:
        if not (is_manager or is_submitter):
            messages.error(request, 'You do not have permission to edit this document.')
            return redirect('document-detail', pk=document.pk)
    elif document.status == Document.STATUS_APPROVED:
        if not is_manager:
            messages.error(request, 'Only administrators can edit an approved document.')
            return redirect('document-detail', pk=document.pk)

    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=document)
        if form.is_valid():
            document = form.save()
            save_document_images(request, document)
            log_audit(document, 'edit', user, notes='DocumentEdit')
            messages.success(request, f'Document "{document.title}" has been updated.')
            return redirect('document-detail', pk=document.pk)
    else:
        form = DocumentForm(instance=document)

    return render(request, 'documents/document_form.html', {
        'form': form,
        'document': document,
        'action': 'Edit'
    })

@login_required
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    user = request.user
    employee = getattr(user, 'employee', None)
    is_manager = employee and employee.role in ['admin', 'manager']
    is_submitter = document.submitted_by_id == user.id

    if document.status == Document.STATUS_PENDING:
        messages.warning(request, 'A document that is pending review cannot be deleted.')
        return redirect('document-detail', pk=document.pk)

    if document.status in [Document.STATUS_DRAFT, Document.STATUS_REJECTED]:
        if not (is_manager or is_submitter):
            messages.error(request, 'You do not have permission to delete this document.')
            return redirect('document-detail', pk=document.pk)
    elif document.status == Document.STATUS_APPROVED:
        if not is_manager:
            messages.error(request, 'Only administrators can delete an approved document.')
            return redirect('document-detail', pk=document.pk)

    if request.method == 'POST':
        title = document.title
        log_audit(document, 'delete', user)
        document.delete()
        messages.success(request, f'Document「{title}" has been deleted.')
        return redirect('documents-dashboard')
    return render(request, 'documents/document_confirm_delete.html', {'document': document})

# Category Views
@login_required
@role_required('admin', 'manager')
def category_list(request):
    categories = DocumentCategory.objects.all()
    return render(request, 'documents/category_list.html', {'categories': categories})

@login_required
@role_required('admin', 'manager')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category \"{category.name}\" was created successfully.")
            return redirect('category-list')
    else:
        form = CategoryForm()
    return render(request, 'documents/category_form.html', {'form': form, 'action': 'Create'})

@login_required
@role_required('admin', 'manager')
def category_edit(request, pk):
    category = get_object_or_404(DocumentCategory, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category \"{category.name}\" has been updated.")
            return redirect('category-list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'documents/category_form.html', {
        'form': form, 
        'category': category, 
        'action': 'Edit'
    })

@login_required
@role_required('admin', 'manager')
def category_delete(request, pk):
    category = get_object_or_404(DocumentCategory, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category \"{name}\" has been deleted.")
        return redirect('category-list')
    return render(request, 'documents/category_confirm_delete.html', {'category': category})


# ── Document Approval Flow ──────────────────────────────────────────────────

@login_required
def document_submit(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if document.status != Document.STATUS_DRAFT and document.status != Document.STATUS_REJECTED:
        messages.warning(request, "Only draft or rejected documents can be submitted for review.")
        return redirect('document-detail', pk=document.pk)
    if request.method == 'POST':
        form = DocumentSubmitForm(request.POST)
        if form.is_valid():
            previous_status = document.status
            if document.status == Document.STATUS_REJECTED:
                document.version += 1
            document.status = Document.STATUS_PENDING
            document.review_notes = form.cleaned_data.get('review_notes', '').strip()
            document.submitted_at = timezone.now()
            document.submitted_by = request.user
            document.save()
            log_audit(document, 'submit', request.user, previous_status=previous_status, new_status=document.status, notes=document.review_notes)
            messages.success(request, f"Document \"{document.title}\" has been submitted for review.")
            return redirect('document-detail', pk=document.pk)
    else:
        form = DocumentSubmitForm()
    return render(request, 'documents/document_submit.html', {'document': document, 'form': form})

@login_required
@role_required('admin', 'manager')
def document_review(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if document.status != Document.STATUS_PENDING:
        messages.warning(request, "Only documents that are pending review can be reviewed.")
        return redirect('document-detail', pk=document.pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('review_notes', '').strip()
        if action == 'approve':
            document.status = Document.STATUS_APPROVED
            document.is_active = True
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.review_notes = notes
            document.save()
            log_audit(document, 'approve', request.user, previous_status=Document.STATUS_PENDING, new_status=Document.STATUS_APPROVED, notes=notes)
            messages.success(request, f"Document「{document.title}」Approved。")
            return redirect('documents-dashboard')
        elif action == 'reject':
            document.status = Document.STATUS_REJECTED
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.review_notes = notes
            document.save()
            log_audit(document, 'reject', request.user, previous_status=Document.STATUS_PENDING, new_status=Document.STATUS_REJECTED, notes=notes)
            messages.warning(request, f"Document「{document.title}」Rejected。")
            return redirect('documents-dashboard')
    return render(request, 'documents/document_review.html', {'document': document})

@login_required
def document_recall(request, pk):
    document = get_object_or_404(Document, pk=pk)
    employee = getattr(request.user, 'employee', None)
    if document.status != Document.STATUS_PENDING:
        messages.warning(request, "Only documents that are pending review can be withdrawn.")
        return redirect('document-detail', pk=document.pk)
    if document.submitted_by_id != request.user.id:
        messages.error(request, 'Only the person who submitted the document can withdraw it.')
        return redirect('document-detail', pk=document.pk)
    if request.method == 'POST':
        previous_status = document.status
        document.status = Document.STATUS_DRAFT
        document.save()
        log_audit(document, 'recall', request.user, previous_status=previous_status, new_status=Document.STATUS_DRAFT)
        messages.info(request, f"Document \"{document.title}\" was withdrawn from review and is back to draft.")
    return redirect('document-detail', pk=document.pk)


# ── Audit / History ─────────────────────────────────────────────────────────

@login_required
def document_audit_logs(request, pk):
    document = get_object_or_404(Document, pk=pk)
    logs = DocumentAuditLog.objects.filter(document=document)
    return render(request, 'documents/document_audit_logs.html', {'document': document, 'logs': logs})


@login_required
@role_required('admin', 'manager')
def audit_dashboard(request):
    logs = DocumentAuditLog.objects.select_related('document', 'performed_by').all()
    return render(request, 'documents/audit_dashboard.html', {'logs': logs})


# ── Active Toggle ────────────────────────────────────────────────────────────

@login_required
@role_required('admin', 'manager')
def document_toggle_active(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        previous_status = document.status
        document.is_active = not document.is_active
        document.save()
        log_audit(
            document,
            'toggle_active',
            request.user,
            previous_status=previous_status,
            new_status=document.status,
            notes=f"Status changed to: {'Enabled' if document.is_active else 'Disabled'}"
        )
        state = 'Enabled' if document.is_active else 'Disabled'
        messages.success(request, f"Document \"{document.title}\" is now {state}.")
    return redirect('document-detail', pk=document.pk)


@login_required
def check_doc_code(request):
    code = request.GET.get('code', '').strip()
    exclude_pk = request.GET.get('pk')

    if not code:
        return JsonResponse({'available': False, 'message': 'Please enter a document code'})
    if len(code) < 3:
        return JsonResponse({'available': False, 'message': 'The document code must be at least 3 characters long'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', code):
        return JsonResponse({'available': False, 'message': 'Cannot contain special characters'})

    qs = Document.objects.filter(code=code)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This code already exists, please choose another one'})
    return JsonResponse({'available': True, 'message': 'This code is available'})


@login_required
def load_department_reviewers(request):
    dept_id = request.GET.get('department_id')
    options = []
    if dept_id:
        reviewers = Employee.objects.filter(department_id=dept_id, role__in=['manager', 'admin']).order_by('name')
        options = [{'id': e.pk, 'name': f"{e.emp_no} - {e.name}"} for e in reviewers]
    return JsonResponse({'options': options})
