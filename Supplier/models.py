from django.db import models


class SupplierCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Category Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Supplier Category'
        verbose_name_plural = 'Supplier Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    supplier_id = models.CharField(max_length=50, unique=True, verbose_name='Supplier ID')
    name = models.CharField(max_length=100, verbose_name='Supplier Name')
    category = models.ForeignKey(
        SupplierCategory, on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Supplier Category', related_name='suppliers'
    )
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name='Contact Person')
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name='Phone')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name='Address')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['supplier_id']

    def __str__(self):
        return f"{self.supplier_id} - {self.name}"

    @property
    def material_count(self):
        return self.materials.count()

    @property
    def equipment_count(self):
        return self.equipments.count()
