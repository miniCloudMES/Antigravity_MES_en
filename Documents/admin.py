from django.contrib import admin
from .models import DocumentCategory, Document, DocumentImage, DocumentAuditLog

class DocumentImageInline(admin.TabularInline):
    model = DocumentImage
    extra = 1

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    list_filter = ['name']
    search_fields = ['name']
    ordering = ['name']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'created_at']
    list_filter = ['category']
    search_fields = ['title']
    ordering = ['title']
    inlines = [DocumentImageInline]

@admin.register(DocumentImage)
class DocumentImageAdmin(admin.ModelAdmin):
    list_display = ('document', 'description', 'created_at')
    search_fields = ('document__title', 'description')
    autocomplete_fields = ('document',)

@admin.register(DocumentAuditLog)
class DocumentAuditLogAdmin(admin.ModelAdmin):
    list_display = ('document', 'action', 'performed_by', 'performed_at', 'previous_status', 'new_status')
    list_filter = ('action', 'performed_at')
    search_fields = ('document__title', 'notes')
    date_hierarchy = 'performed_at'
    autocomplete_fields = ('document',)
    readonly_fields = ('document', 'action', 'performed_by', 'performed_at', 'previous_status', 'new_status', 'notes')
