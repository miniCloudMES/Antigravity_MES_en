"""File library video standardized transcoding: 720p max + H.264 (libx264) + MP4, executed in background thread"""
import os
import re
import subprocess
import threading
import uuid

from django.conf import settings

FFMPEG_BIN = getattr(settings, 'FFMPEG_BIN', 'ffmpeg')
VIDEO_CRF = 23                # Quality parameter (H.264 recommended 18-28, lower is higher quality)
VIDEO_PRESET = 'medium'       # Speed / compression balance
AUDIO_BITRATE = '128k'
MAX_WIDTH = 1280              # 720p max width
MAX_HEIGHT = 720              # 720p max height
TRANSCODE_TIMEOUT = 3600      # Max 1 hour per file


def _mark_failed(lib_file, msg):
    lib_file.video_status = 'FAILED'
    lib_file.video_error = (msg or '')[:500]
    lib_file.save(update_fields=['video_status', 'video_error'])


def transcode_video(lib_file_id, sync=False):
    """Transcode video to max 720p / H.264 / MP4 and save as video_standard.
    When sync=True, run synchronously (for management commands/cron); otherwise in background thread.
    """
    from .models import LibraryFile

    def run():
        lib_file = LibraryFile.objects.filter(pk=lib_file_id).first()
        if not lib_file or not lib_file.file:
            return

        try:
            src_path = lib_file.file.path
        except (OSError, ValueError):
            _mark_failed(lib_file, 'Source file could not be read')
            return

        if not os.path.isfile(src_path):
            _mark_failed(lib_file, 'Source file does not exist')
            return

        lib_file.video_status = 'PROCESSING'
        lib_file.video_error = None
        lib_file.save(update_fields=['video_status', 'video_error'])

        # Output filename: <base>_<uuid8>_720p.mp4 (avoids path traversal and collisions)
        base = os.path.splitext(os.path.basename(src_path))[0]
        safe = re.sub(r'[^A-Za-z0-9_.\-]', '_', base)[:80] or 'video'
        out_name = f"file_library/{safe}_{uuid.uuid4().hex[:8]}_720p.mp4"
        out_path = os.path.join(settings.MEDIA_ROOT, out_name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # scale: min(1280,iw) / min(720,ih) downscale only; force_original_aspect_ratio keeps aspect ratio.
        # Note: commas in filter must be escaped with \, and libx264 requires even dimensions -> pad.
        vf = (
            "scale=min({0}\\,iw):min({1}\\,ih):force_original_aspect_ratio=decrease,"
            "pad=ceil(iw/2)*2:ceil(ih/2)*2"
        ).format(MAX_WIDTH, MAX_HEIGHT)
        cmd = [
            FFMPEG_BIN, '-y', '-hide_banner', '-loglevel', 'error',
            '-i', src_path,
            '-vf', vf,
            '-c:v', 'libx264',
            '-preset', VIDEO_PRESET,
            '-crf', str(VIDEO_CRF),
            '-c:a', 'aac',
            '-b:a', AUDIO_BITRATE,
            '-movflags', '+faststart',
            out_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=TRANSCODE_TIMEOUT)
        except subprocess.TimeoutExpired:
            _mark_failed(lib_file, 'Transcoding timed out (exceeded 1 hour)')
            return
        except Exception as e:
            _mark_failed(lib_file, f'Transcoding failed to execute: {e}')
            return

        if proc.returncode != 0 or not os.path.isfile(out_path):
            err = (proc.stderr or b'').decode('utf-8', errors='replace')
            _mark_failed(lib_file, f'ffmpeg error: {err[-400:]}')
            return

        # Success: attach standardized version
        lib_file.video_standard.name = out_name
        lib_file.video_status = 'COMPLETED'
        lib_file.video_error = None
        lib_file.save(update_fields=['video_standard', 'video_status', 'video_error'])

    if sync:
        run()
        return None
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
