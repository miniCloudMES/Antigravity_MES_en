from django.db import models
from django.contrib.auth.models import User
import os
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver

class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Category Name")
    description = models.TextField(blank=True, null=True, verbose_name="CategoryDescription")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Document Category"
        verbose_name_plural = "Document Category"
        ordering = ['name']

    def __str__(self):
        return self.name

class Document(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    title = models.CharField(max_length=200, verbose_name="Document Title")
    code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Document Code")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    category = models.ForeignKey(
        DocumentCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="documents", 
        verbose_name="Document Category"
    )
    department = models.ForeignKey(
        'Orgnization.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        verbose_name="Department"
    )
    content = models.TextField(verbose_name="Document Content")
    version = models.PositiveIntegerField(default=1, verbose_name="Version")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default=STATUS_DRAFT, 
        verbose_name="Review Status"
    )
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Submitted At")
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_documents',
        verbose_name="Submitted By"
    )
    is_active = models.BooleanField(default=False, verbose_name="Status")
    expired_at = models.DateTimeField(null=True, blank=True, verbose_name="Expiry Date")
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_documents', 
        verbose_name="Reviewed By"
    )
    approval_manager = models.ForeignKey(
        'Orgnization.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_documents',
        verbose_name="Approval Manager"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Reviewed At")
    review_notes = models.TextField(blank=True, verbose_name="Review Notes")
    # Keep this for compatibility, but we will primarily use the multiple images model below
    image = models.ImageField(
        upload_to='document_images/', 
        null=True, 
        blank=True, 
        verbose_name="Document Main Image (Legacy)"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Created By"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Document"
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

class DocumentImage(models.Model):
    document = models.ForeignKey(
        Document, 
        on_delete=models.CASCADE, 
        related_name='images', 
        verbose_name="Related Documents"
    )
    image = models.ImageField(upload_to='document_images/', verbose_name="Image")
    description = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="ImageDescription"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "DocumentImage"
        verbose_name_plural = "DocumentImage"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.document.title} - Image ({self.id})"


class DocumentAuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
        ('submit', 'Submit for Review'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('recall', 'Withdraw Submission'),
        ('toggle_active', 'Active/Disabled toggle'),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name="Document"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Performed By"
    )
    performed_at = models.DateTimeField(auto_now_add=True, verbose_name="Performed At")
    previous_status = models.CharField(max_length=20, blank=True, null=True, verbose_name="Previous Status")
    new_status = models.CharField(max_length=20, blank=True, null=True, verbose_name="New Status")
    notes = models.TextField(blank=True, null=True, verbose_name="Remarks")

    class Meta:
        verbose_name = "Document Audit Log"
        verbose_name_plural = "Document Audit Logs"
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.document.title} - {self.get_action_display()} - {self.performed_at:%Y-%m-%d %H:%M}"

# Clean up physical files on deletion
@receiver(post_delete, sender=Document)
def auto_delete_document_image(sender, instance, **kwargs):
    if instance.image and bool(instance.image.name):
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

@receiver(post_delete, sender=DocumentImage)
def auto_delete_document_subimage(sender, instance, **kwargs):
    if instance.image and bool(instance.image.name):
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
