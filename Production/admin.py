from django.contrib import admin
from .models import WorkOrder, BOM, BOMItem, ProcessStep, WorkOrderStep


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'lot_number', 'product', 'quantity', 'status', 'planned_start_date', 'planned_end_date')
    list_filter = ('status', 'product', 'customer')
    search_fields = ('order_number', 'lot_number', 'product__name', 'customer__name')
    date_hierarchy = 'created_at'


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 1
    autocomplete_fields = ['component']


@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = ('product', 'version', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('product__name', 'product__product_id')
    inlines = [BOMItemInline]


@admin.register(BOMItem)
class BOMItemAdmin(admin.ModelAdmin):
    list_display = ('bom', 'component', 'quantity')
    search_fields = ('bom__product__name', 'component__name', 'component__material_id')
    autocomplete_fields = ('bom', 'component')


class WorkOrderStepInline(admin.TabularInline):
    model = WorkOrderStep
    extra = 0
    fields = ('step_number', 'name', 'status', 'personnel', 'equipment', 'material', 'standard_time_minutes')


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ('product', 'step_number', 'name', 'personnel', 'equipment', 'material', 'standard_time_minutes')
    list_filter = ('product',)
    search_fields = ('product__product_id', 'product__name', 'name')
    ordering = ('product', 'step_number')


@admin.register(WorkOrderStep)
class WorkOrderStepAdmin(admin.ModelAdmin):
    list_display = ('work_order', 'step_number', 'name', 'status')
    list_filter = ('status',)
    search_fields = ('work_order__order_number', 'name')
    ordering = ('work_order', 'step_number')
