from django import forms
from django.forms import inlineformset_factory
from Material.models import Material
from Product.models import Product
from Customer.models import Customer
from .models import WorkOrder, BOM, BOMItem, ProcessStep, WorkOrderStep


class ProductChoiceField(forms.ModelChoiceField):
    """Only show active products"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('queryset', Product.objects.filter(is_active=True))
        kwargs.setdefault('empty_label', '--- Select Product ---')
        super().__init__(*args, **kwargs)


class WorkOrderForm(forms.ModelForm):
    product = ProductChoiceField()

    class Meta:
        model = WorkOrder
        fields = [
            'order_number',
            'customer',
            'lot_number',
            'product',
            'quantity',
            'type',
            'source',
            'planned_start_date',
            'planned_end_date',
            'actual_start_date',
            'actual_end_date',
            'notes',
        ]
        widgets = {
            'planned_start_date': forms.DateTimeInput(attrs={'type': 'text', 'class': 'form-control datepicker'}),
            'planned_end_date': forms.DateTimeInput(attrs={'type': 'text', 'class': 'form-control datepicker'}),
            'actual_start_date': forms.DateTimeInput(attrs={'type': 'text', 'class': 'form-control datepicker'}),
            'actual_end_date': forms.DateTimeInput(attrs={'type': 'text', 'class': 'form-control datepicker'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter remarks...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'customer' in self.fields:
            self.fields['customer'].queryset = Customer.objects.filter(is_active=True)
            self.fields['customer'].empty_label = '--- Select Customer (optional) ---'
            self.fields['customer'].required = False
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'


class BOMForm(forms.ModelForm):
    product = ProductChoiceField()

    class Meta:
        model = BOM
        fields = ['product', 'version', 'description', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class BOMItemForm(forms.ModelForm):
    class Meta:
        model = BOMItem
        fields = ['component', 'quantity', 'unit', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


BOMItemFormSet = inlineformset_factory(
    BOM,
    BOMItem,
    form=BOMItemForm,
    extra=1,
    can_delete=True,
)


class ProcessStepForm(forms.ModelForm):
    class Meta:
        model = ProcessStep
        fields = ['step_number', 'name', 'personnel', 'description', 'personnel_requirement',
                  'equipment', 'material', 'document', 'qc_requirements', 'standard_time_minutes']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control quill-input', 'rows': 4}),
            'personnel_requirement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Additional description (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'description':
                continue  # description is already a Quill textarea (keep quill-input class)
            if field_name == 'personnel':
                field.widget.attrs['class'] = 'form-select'
                field.empty_label = '--- Select Position ---'
                continue
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


ProcessStepFormSet = inlineformset_factory(
    Product,
    ProcessStep,
    form=ProcessStepForm,
    extra=1,
    can_delete=True,
    fk_name='product',
)


class WorkOrderStepTrackInForm(forms.ModelForm):
    """Track In form: confirm received quantity and record track-in note/condition"""

    class Meta:
        model = WorkOrderStep
        fields = ['received_quantity', 'track_in_note']
        labels = {'received_quantity': 'Received Quantity'}
        widgets = {
            'received_quantity': forms.NumberInput(attrs={'class': 'form-control text-center', 'min': 0}),
            'track_in_note': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'e.g. appearance defect, previous-station issue, material shortage, awaiting confirmation...',
            }),
        }


class WorkOrderStepQuantityForm(forms.ModelForm):
    class Meta:
        model = WorkOrderStep
        fields = ['received_quantity', 'good_quantity', 'defect_quantity', 'loss_quantity', 'remarks', 'track_out_note']
        labels = {'received_quantity': 'Received Quantity'}
        widgets = {
            'track_out_note': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Issues found on track out, e.g. good-part defect, equipment problem, quantity discrepancy...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'track_out_note':
                continue  # keep default styling for textarea
            field.widget.attrs['class'] = 'form-control text-center'
            field.widget.attrs['min'] = 0


class WorkOrderStepForm(forms.ModelForm):
    class Meta:
        model = WorkOrderStep
        fields = ['step_number', 'name', 'personnel', 'description', 'personnel_requirement',
                  'equipment', 'material', 'document', 'qc_requirements',
                  'standard_time_minutes', 'status',
                  'received_quantity', 'good_quantity', 'defect_quantity', 'loss_quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'personnel':
                field.widget.attrs['class'] = 'form-select'
                field.empty_label = '--- Select Position ---'
                continue
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


WorkOrderStepFormSet = inlineformset_factory(
    WorkOrder,
    WorkOrderStep,
    form=WorkOrderStepForm,
    extra=1,
    can_delete=True,
)