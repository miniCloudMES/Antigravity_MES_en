from django.contrib import admin
from .models import ProductCategory, Product, ProductStockTransaction


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'name', 'category', 'unit', 'stock_quantity', 'min_stock', 'version', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active')
    search_fields = ('product_id', 'name', 'spec')


@admin.register(ProductStockTransaction)
class ProductStockTransactionAdmin(admin.ModelAdmin):
    list_display = ('type', 'product', 'quantity', 'reference', 'created_by', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('product__product_id', 'reference', 'remark')
