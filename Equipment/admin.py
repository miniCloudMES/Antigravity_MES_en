from django.contrib import admin
from .models import EquipmentCategory, Equipment, MaintenanceRecord


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('equipment_id', 'name', 'category', 'status', 'supplier', 'location', 'purchase_date', 'updated_at')
    list_filter = ('category', 'status', 'supplier')
    search_fields = ('equipment_id', 'name', 'location')
    list_select_related = ('category', 'supplier')


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'type', 'performed_by', 'start_time', 'end_time')
    list_filter = ('type', 'start_time')
    search_fields = ('equipment__equipment_id', 'equipment__name', 'remark')
    date_hierarchy = 'start_time'
    autocomplete_fields = ('equipment',)
