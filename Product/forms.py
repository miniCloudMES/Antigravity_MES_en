from django import forms
from .models import ProductCategory, Product, ProductStockTransaction
import re
from django.core.exceptions import ValidationError


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electronic product'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'CategoryDescriptionDescription'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_id', 'name', 'category', 'unit', 'spec', 'drawing_no', 'version', 'image', 'min_stock', 'notes', 'is_active']
        widgets = {
            'product_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PRD-2024-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'spec': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specification (e.g. 300x200x50mm)'}),
            'drawing_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Drawing No.'}),
            'version': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Version'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'placeholder': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'OtherNotes'}),
        }

    def clean_product_id(self):
        product_id = self.cleaned_data['product_id'].strip()
        if len(product_id) < 3:
            raise ValidationError('Product ID requires at least 3 characters')
        if not re.match(r'^[A-Za-z0-9_\-]+$', product_id):
            raise ValidationError('Cannot contain special characters')
        qs = Product.objects.filter(product_id=product_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('This product ID already exists.')
        return product_id


class ProductStockTransactionForm(forms.ModelForm):
    class Meta:
        model = ProductStockTransaction
        fields = ['product', 'type', 'quantity', 'reference', 'remark']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Work order / sales order no.'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Remarks (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        self.product_instance = kwargs.pop('product_instance', None)
        super().__init__(*args, **kwargs)
        if self.product_instance:
            self.fields['product'].initial = self.product_instance
        self.fields['product'].disabled = bool(self.product_instance)
        self.fields['quantity'].min_value = None
        self.fields['quantity'].widget.attrs.pop('min', None)
        self.fields['quantity'].help_text = 'Inbound/Outbound must be positive; Adjustment may be negative (reduces stock)'

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        txn_type = self.cleaned_data.get('type')
        # Inbound/Outbound must be positive; Adjustment allows both signs (positive = add stock, negative = remove stock)
        if txn_type != 'ADJUST' and qty <= 0:
            raise ValidationError('Quantity must be greater than 0.')
        return qty

    def clean(self):
        cleaned = super().clean()
        txn_type = cleaned.get('type')
        qty = cleaned.get('quantity')
        prod = self.product_instance or cleaned.get('product')
        if not prod:
            return cleaned
        if txn_type == 'OUTBOUND' and prod.stock_quantity < qty:
            raise ValidationError('Outbound quantity cannot exceed the current stock.')
        if txn_type == 'ADJUST' and qty < 0 and prod.stock_quantity + qty < 0:
            raise ValidationError('Stock after adjustment cannot be negative.')
        return cleaned
