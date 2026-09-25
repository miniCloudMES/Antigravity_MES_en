from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('INBOUND', 'Inbound'),
        ('OUTBOUND', 'Outbound'),
        ('ADJUST', 'Adjustment'),
    ]

    material = models.ForeignKey('Material', on_delete=models.PROTECT, related_name='stock_transactions', verbose_name='Material')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='Transaction Type')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Quantity')
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Balance After')
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Reference No.')
    remark = models.TextField(blank=True, null=True, verbose_name='Remarks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transactions', verbose_name='Operator')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    class Meta:
        verbose_name = 'Stock Transaction Record'
        verbose_name_plural = 'Stock Transaction Records'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} {self.material.material_id} x{self.quantity}"


class MaterialCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Category Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Material Category'
        verbose_name_plural = 'Material Category'
        ordering = ['name']

    def __str__(self):
        return self.name


class Material(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Piece (pcs)'),
        ('kg', 'Kilogram (kg)'),
        ('g', 'Gram (g)'),
        ('m', 'Meter (m)'),
        ('cm', 'Centimeter (cm)'),
        ('L', 'Liter (L)'),
        ('box', 'Box'),
        ('set', 'Set'),
        ('roll', 'Roll'),
        ('sheet', 'Sheet'),
    ]

    material_id = models.CharField(max_length=50, unique=True, verbose_name='Material ID')
    name = models.CharField(max_length=100, verbose_name='Material Name')
    category = models.ForeignKey(
        MaterialCategory, on_delete=models.PROTECT,
        verbose_name='Material Category', related_name='materials'
    )
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pcs', verbose_name='Unit')
    image = models.ImageField(upload_to='material_images/', blank=True, null=True, verbose_name='Material Image')
    stock_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name='StockQuantity'
    )
    min_stock = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, blank=True, null=True, verbose_name='Safety Stock Level'
    )
    supplier = models.ForeignKey(
        'Supplier.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materials',
        verbose_name='Supplier',
    )
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name='Location')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Material'
        ordering = ['material_id']

    def __str__(self):
        return f"{self.material_id} - {self.name}"

    @property
    def is_low_stock(self):
        if self.min_stock is not None and self.min_stock > 0:
            return self.stock_quantity <= self.min_stock
        return False
