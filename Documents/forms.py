from django import forms
from .models import DocumentCategory, Document

class CategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter category description (optional)'}),
        }

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['code', 'title', 'description', 'category', 'department', 'approval_manager', 'content', 'expired_at']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. DOC-001'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter document title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter description (optional)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'approval_manager': forms.Select(attrs={'class': 'form-select', 'id': 'id_approval_manager'}),
            'content': forms.HiddenInput(attrs={'id': 'quill-content-input'}),
            'expired_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dept = None
        if self.instance and self.instance.pk:
            dept = self.instance.department
        elif 'department' in self.data:
            from Orgnization.models import Department
            dept_id = self.data.get('department')
            if dept_id:
                try:
                    dept = Department.objects.get(pk=dept_id)
                except Department.DoesNotExist:
                    pass
        if dept:
            self.fields['approval_manager'].queryset = self._get_reviewers(dept)
        else:
            self.fields['approval_manager'].queryset = self.fields['approval_manager'].queryset.none()
        self.fields['approval_manager'].empty_label = 'Select a department first'

    def _get_reviewers(self, dept):
        from Orgnization.models import Employee
        return Employee.objects.filter(department=dept, role__in=['manager', 'admin']).order_by('name')

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip()
        if not code:
            return code
        qs = Document.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This document code is already in use. Please choose another one.')
        return code

class DocumentSubmitForm(forms.Form):
    review_notes = forms.CharField(
        label='Review Notes', 
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter submission notes (optional)'})
    )
