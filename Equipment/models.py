from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class EquipmentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Category Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Equipment Category'
        verbose_name_plural = 'Equipment Category'
        ordering = ['name']

    def __str__(self):
        return self.name


class Equipment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('broken', 'Broken Down'),
        ('retired', 'Retired'),
    ]

    equipment_id = models.CharField(max_length=50, unique=True, verbose_name='Equipment ID')
    name = models.CharField(max_length=100, verbose_name='Equipment Name')
    category = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, verbose_name='Equipment Category', related_name='equipments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Equipment Status')
    purchase_date = models.DateField(blank=True, null=True, verbose_name='Purchase Date')
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name='Location')
    supplier = models.ForeignKey(
        'Supplier.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipments',
        verbose_name='Supplier',
    )
    image = models.ImageField(upload_to='equipment_images/', blank=True, null=True, verbose_name='Equipment Image')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Equipment'
        verbose_name_plural = 'Equipment'
        ordering = ['equipment_id']

    def __str__(self):
        return f"{self.equipment_id} - {self.name}"


class MaintenanceRecord(models.Model):
    MAINTENANCE_TYPES = [
        ('preventive', 'Preventive Maintenance'),
        ('corrective', 'Broken DownMaintenance'),
        ('inspection', 'Inspection / Calibration'),
        ('other', 'Other'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_records', verbose_name='Equipment')
    type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES, verbose_name='Maintenance Type')
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_records', verbose_name='Performed By')
    start_time = models.DateTimeField(verbose_name='Start Time')
    end_time = models.DateTimeField(blank=True, null=True, verbose_name='End Time')
    remark = models.TextField(blank=True, null=True, verbose_name='Description')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    class Meta:
        verbose_name = 'Equipment Maintenance Record'
        verbose_name_plural = 'Equipment Maintenance Records'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.equipment.equipment_id} {self.get_type_display()} {self.start_time:%Y-%m-%d}"
