from django import forms
from .models import Department, Position, Employee


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['code', 'name', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. DEP-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter department name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Department description'}),
        }


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['code', 'name', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. POS-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter position name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Position description'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip()
        qs = Position.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This Position Code is already in use. Please use another.')
        return code


class EmployeeForm(forms.ModelForm):
    create_account = forms.BooleanField(
        label='Create System Account',
        required=False,
        initial=True,
        help_text='When checked, an account will be created with the Employee ID and linked to this employee',
    )
    generate_password = forms.CharField(
        label='Initial Password',
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to generate automatically'}),
    )

    class Meta:
        model = Employee
        fields = [
            'emp_no', 'name', 'gender', 'department', 'position',
            'role', 'email', 'phone', 'hire_date', 'photo', 'is_active'
        ]
        widgets = {
            'emp_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter employee name'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@company.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +1 555 123 4567'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].empty_label = 'No department assigned'
        self.fields['position'].empty_label = 'No position assigned'
        instance = kwargs.get('instance')
        if instance and instance.user_id:
            self.fields['create_account'].widget = forms.HiddenInput()
            self.fields['create_account'].initial = False
            self.fields['create_account'].disabled = True
            self.fields.pop('generate_password', None)

    def save(self, commit=True):
        employee = super().save(commit=False)
        created_user = None
        generated_pw = None

        if self.cleaned_data.get('create_account') and not employee.user:
            User = self._get_user_model()
            username = self._build_username(employee.emp_no)
            generated_pw = self.cleaned_data.get('generate_password') or self._generate_password()
            created_user = User.objects.create_user(
                username=username,
                email=employee.email or '',
                password=generated_pw,
            )
            employee.user = created_user

        if commit:
            employee.save()
            self.save_m2m()

        return employee, created_user, generated_pw

    def _build_username(self, emp_no: str) -> str:
        emp_no = (emp_no or '').strip()
        if not emp_no:
            emp_no = f"emp_{__import__('uuid').uuid4().hex[:6]}"
        return emp_no

    def _generate_password(self, length: int = 10) -> str:
        import secrets, string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _get_user_model(self):
        from django.contrib.auth import get_user_model
        return get_user_model()
