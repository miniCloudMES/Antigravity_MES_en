from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Category Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Category'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Piece (pcs)'),
        ('set', 'Set'),
        ('box', 'Box'),
        ('kg', 'Kilogram (kg)'),
        ('g', 'Gram (g)'),
        ('m', 'Meter (m)'),
        ('L', 'Liter (L)'),
    ]

    product_id = models.CharField(max_length=50, unique=True, verbose_name='Product ID')
    name = models.CharField(max_length=100, verbose_name='Product Name')
    category = models.ForeignKey(
        ProductCategory, on_delete=models.PROTECT,
        verbose_name='Product Category', related_name='products'
    )
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pcs', verbose_name='Unit')
    spec = models.CharField(max_length=200, blank=True, null=True, verbose_name='Specification')
    image = models.ImageField(upload_to='product_images/', blank=True, null=True, verbose_name='Product Image')
    drawing_no = models.CharField(max_length=100, blank=True, null=True, verbose_name='Drawing No.')
    version = models.CharField(max_length=20, blank=True, null=True, verbose_name='Version')
    stock_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name='StockQuantity'
    )
    min_stock = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, blank=True, null=True, verbose_name='Safety Stock Level'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Product'
        ordering = ['product_id']

    def __str__(self):
        return f"{self.product_id} - {self.name}"

    @property
    def is_low_stock(self):
        if self.min_stock is not None and self.min_stock > 0:
            return self.stock_quantity <= self.min_stock
        return False


class ProductStockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('INBOUND', 'Inbound'),
        ('OUTBOUND', 'Outbound'),
        ('ADJUST', 'Adjustment'),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name='stock_transactions', verbose_name='Product'
    )
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='Transaction Type')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Quantity')
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Balance After')
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Reference No.')
    remark = models.TextField(blank=True, null=True, verbose_name='Remarks')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='product_stock_transactions', verbose_name='Operator'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    class Meta:
        verbose_name = 'Product Stock Transaction Record'
        verbose_name_plural = 'Product Stock Transaction Records'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} {self.product.product_id} x{self.quantity}"
