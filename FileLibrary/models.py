from django.db import models
from django.contrib.auth.models import User
import os


class FileCategory(models.Model):
    """File Category"""
    name = models.CharField(max_length=100, verbose_name="Category Name")
    description = models.TextField(blank=True, null=True, verbose_name="CategoryDescription")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "File Category"
        verbose_name_plural = "File Category"
        ordering = ['name']

    def __str__(self):
        return self.name


class LibraryFile(models.Model):
    """Library File"""
    category = models.ForeignKey(
        FileCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='files',
        verbose_name="Category"
    )
    title = models.CharField(max_length=200, verbose_name="File Name")
    file = models.FileField(upload_to='file_library/', verbose_name="File")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    # Video standardization (720p / H.264 / MP4)
    VIDEO_STATUS_CHOICES = [
        ('PENDING', 'Pending Transcode'),
        ('PROCESSING', 'Transcoding'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Transcode Failed'),
    ]
    video_status = models.CharField(
        max_length=20, choices=VIDEO_STATUS_CHOICES, blank=True, null=True,
        verbose_name='Video Transcode Status',
    )
    video_standard = models.FileField(
        upload_to='file_library/', blank=True, null=True, verbose_name='Standardized Video'
    )
    video_error = models.CharField(max_length=500, blank=True, null=True, verbose_name='Transcode Error Message')
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_files',
        verbose_name="Uploaded By"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "File"
        verbose_name_plural = "File"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def size_display(self):
        try:
            size = self.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / 1024 / 1024:.1f} MB"
        except (OSError, ValueError):
            return "-"

    def _icon_for_ext(self, ext):
        """Return (bootstrap icon class, color class) by file extension"""
        ext = ext.lower()
        if ext in {'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico', 'tiff', 'heic'}:
            return 'bi-file-earmark-image', 'text-info'
        if ext in {'pdf'}:
            return 'bi-file-earmark-pdf', 'text-danger'
        if ext in {'doc', 'docx', 'odt', 'rtf'}:
            return 'bi-file-earmark-word', 'text-primary'
        if ext in {'xls', 'xlsx', 'csv', 'ods'}:
            return 'bi-file-earmark-excel', 'text-success'
        if ext in {'ppt', 'pptx', 'odp'}:
            return 'bi-file-earmark-ppt', 'text-warning'
        if ext in {'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz'}:
            return 'bi-file-earmark-zip', 'text-secondary'
        if ext in {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v'}:
            return 'bi-file-earmark-play', 'text-danger'
        if ext in {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'wma'}:
            return 'bi-file-earmark-music', 'text-warning'
        if ext in {'txt', 'md', 'py', 'js', 'ts', 'html', 'css', 'json', 'xml', 'sql', 'log', 'sh', 'c', 'cpp', 'java', 'go', 'rs', 'yaml', 'yml', 'toml', 'ini', 'cfg'}:
            return 'bi-file-earmark-code', 'text-secondary'
        return 'bi-file-earmark', 'text-secondary'

    @property
    def file_icon(self):
        """Return Bootstrap Icons class by file format"""
        return self._icon_for_ext(os.path.splitext(self.filename)[1].lstrip('.'))[0]

    @property
    def file_icon_color(self):
        """Return color class by file format"""
        return self._icon_for_ext(os.path.splitext(self.filename)[1].lstrip('.'))[1]

    IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico', 'svg', 'tiff', 'heic'}
    VIDEO_EXTS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v', 'mpeg', 'mpg', '3gp'}

    @property
    def is_image(self):
        """Whether the file is a previewable image format"""
        ext = os.path.splitext(self.filename)[1].lstrip('.').lower()
        return ext in self.IMAGE_EXTS

    @property
    def is_video(self):
        """Whether the file is a video format (requires standardized transcode)"""
        ext = os.path.splitext(self.filename)[1].lstrip('.').lower()
        return ext in self.VIDEO_EXTS
