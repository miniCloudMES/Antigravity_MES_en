from django.contrib import admin
from .models import MaterialCategory, Material, StockTransaction


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('material_id', 'name', 'category', 'unit', 'stock_quantity', 'min_stock', 'supplier')
    list_filter = ('category', 'unit')
    search_fields = ('material_id', 'name', 'supplier')


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('type', 'material', 'quantity', 'reference', 'created_by', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('material__material_id', 'reference', 'remark')
