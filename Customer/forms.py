from django import forms
from .models import Customer
import re
from django.core.exceptions import ValidationError


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['customer_id', 'name', 'contact_person', 'phone', 'email', 'address', 'tax_id', 'is_active', 'notes']
        widgets = {
            'customer_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CUST-2024-001'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter notes...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name in ('notes', 'customer_id'):
                continue
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_customer_id(self):
        customer_id = self.cleaned_data['customer_id'].strip()
        if len(customer_id) < 3:
            raise ValidationError('Customer ID must be at least 3 characters.')
        if not re.match(r'^[A-Za-z0-9_\-]+$', customer_id):
            raise ValidationError('Customer ID can only contain alphanumeric characters, underscores, and hyphens.')
        qs = Customer.objects.filter(customer_id=customer_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('This Customer ID is already in use. Please enter a different one.')
        return customer_id
