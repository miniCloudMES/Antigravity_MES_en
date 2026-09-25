from django.contrib import admin
from .models import Supplier, SupplierCategory


@admin.register(SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('supplier_id', 'name', 'category', 'contact_person', 'phone', 'email', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active')
    search_fields = ('supplier_id', 'name', 'contact_person', 'phone', 'email')
