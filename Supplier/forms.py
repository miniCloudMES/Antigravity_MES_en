from django import forms
from .models import Supplier, SupplierCategory
import re
from django.core.exceptions import ValidationError


class SupplierCategoryForm(forms.ModelForm):
    class Meta:
        model = SupplierCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electronic Components Supplier'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Category description'}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['supplier_id', 'name', 'category', 'contact_person', 'phone', 'email', 'address', 'notes', 'is_active']
        widgets = {
            'supplier_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SUP-2024-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter supplier name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact person name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company address'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
        }

    def clean_supplier_id(self):
        supplier_id = self.cleaned_data['supplier_id'].strip()
        if len(supplier_id) < 3:
            raise ValidationError('Supplier ID must be at least 3 characters.')
        if not re.match(r'^[A-Za-z0-9_\-]+$', supplier_id):
            raise ValidationError('Supplier ID cannot contain special characters.')
        qs = Supplier.objects.filter(supplier_id=supplier_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('This Supplier ID already exists.')
        return supplier_id
