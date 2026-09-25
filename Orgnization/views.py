from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from .models import Department, Position, Employee
from .forms import DepartmentForm, PositionForm, EmployeeForm
import base64
import uuid
import io
import re


class RoleRequiredMixin:
    """
    View mixin: only allows users holding one of the specified roles.
    Example:
        class MyView(RoleRequiredMixin, ListView):
            allowed_roles = ['admin', 'manager']
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        emp = getattr(request.user, 'employee', None)
        if emp is None or emp.role not in self.allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


@login_required
def check_emp_no(request):
    emp_no = request.GET.get('emp_no', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(emp_no) < 3:
        return JsonResponse({'available': False, 'message': 'Employee ID must be at least 3 characters.'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', emp_no):
        return JsonResponse({'available': False, 'message': 'Special characters not allowed.'})

    qs = Employee.objects.filter(emp_no=emp_no)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This Employee ID already exists.'})
    return JsonResponse({'available': True, 'message': 'This Employee ID is available.'})


@login_required
def check_dept_code(request):
    code = request.GET.get('code', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(code) < 3:
        return JsonResponse({'available': False, 'message': 'Department code must be at least 3 characters.'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', code):
        return JsonResponse({'available': False, 'message': 'Special characters not allowed.'})

    qs = Department.objects.filter(code=code)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This Department code already exists.'})
    return JsonResponse({'available': True, 'message': 'This Department code is available.'})


@login_required
def check_position_code(request):
    code = request.GET.get('code', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(code) < 3:
        return JsonResponse({'available': False, 'message': 'Position code must be at least 3 characters.'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', code):
        return JsonResponse({'available': False, 'message': 'Special characters not allowed.'})

    qs = Position.objects.filter(code=code)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This Position code already exists.'})
    return JsonResponse({'available': True, 'message': 'This Position code is available.'})


class CroppedPhotoMixin:
    """Decode the base64 payload sent by Cropper.js in the front end and inject it into request.FILES['photo']."""

    def post(self, request, *args, **kwargs):
        b64 = request.POST.get('photo_cropped', '').strip()
        if b64:
            # Drop the "data:image/...;base64," prefix
            if ',' in b64:
                b64 = b64.split(',', 1)[1]
            img_bytes = base64.b64decode(b64)
            file_obj = InMemoryUploadedFile(
                file=io.BytesIO(img_bytes),
                field_name='photo',
                name=f"{uuid.uuid4().hex}.jpg",
                content_type='image/jpeg',
                size=len(img_bytes),
                charset=None,
            )
            request.FILES['photo'] = file_obj
        return super().post(request, *args, **kwargs)

@login_required
def index(request):
    return render(request, 'orgnization/index.html')

class OrgDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'orgnization/org_dashboard.html'

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'orgnization/department_list.html'
    context_object_name = 'departments'

class DepartmentCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'orgnization/department_form.html'
    success_url = reverse_lazy('department-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Department "{self.object.name}" has been created.')
        return response

class DepartmentUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'orgnization/department_form.html'
    success_url = reverse_lazy('department-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Department "{self.object.name}" has been updated.')
        return response

class DepartmentDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Department
    template_name = 'orgnization/department_confirm_delete.html'
    success_url = reverse_lazy('department-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Department "{self.object.name}" has been deleted.')
        return super().form_valid(form)

class PositionListView(LoginRequiredMixin, ListView):
    model = Position
    template_name = 'orgnization/position_list.html'
    context_object_name = 'positions'

class PositionCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Position
    form_class = PositionForm
    template_name = 'orgnization/position_form.html'
    success_url = reverse_lazy('position-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Position "{self.object.name}" has been created.')
        return response

class PositionUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Position
    form_class = PositionForm
    template_name = 'orgnization/position_form.html'
    success_url = reverse_lazy('position-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Position "{self.object.name}" has been updated.')
        return response

class PositionDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Position
    template_name = 'orgnization/position_confirm_delete.html'
    success_url = reverse_lazy('position-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Position "{self.object.name}" has been deleted.')
        return super().form_valid(form)

class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'orgnization/employee_list.html'
    context_object_name = 'employees'

    def get_queryset(self):
        return super().get_queryset().select_related('department', 'position')

class EmployeeCreateView(CroppedPhotoMixin, LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'orgnization/employee_form.html'
    success_url = reverse_lazy('employee-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        employee, created_user, generated_pw = form.save(commit=False)
        employee.save()
        form.save_m2m()
        messages.success(self.request, f'Employee "{employee.name}" has been created.')
        if created_user:
            return render(self.request, 'orgnization/account_generated.html', {
                'employee': employee,
                'username': created_user.username,
                'password': generated_pw,
            })
        return redirect(self.success_url)


class EmployeeUpdateView(CroppedPhotoMixin, LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'orgnization/employee_form.html'
    success_url = reverse_lazy('employee-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        employee, created_user, generated_pw = form.save(commit=False)
        employee.save()
        form.save_m2m()
        messages.success(self.request, f'Employee "{employee.name}" has been updated.')
        if created_user:
            return render(self.request, 'orgnization/account_generated.html', {
                'employee': employee,
                'username': created_user.username,
                'password': generated_pw,
            })
        return redirect(self.success_url)

class EmployeeDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Employee
    template_name = 'orgnization/employee_confirm_delete.html'
    success_url = reverse_lazy('employee-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Employee "{self.object.name}" has been deleted.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'orgnization/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['employee'] = getattr(user, 'employee', None)
        return ctx


@login_required
def employee_change_password(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    user = getattr(employee, 'user', None)
    current_employee = getattr(request.user, 'employee', None)
    is_manager = current_employee and current_employee.role in ['admin', 'manager']
    is_self = user == request.user

    if not (is_manager or is_self):
        messages.error(request, 'You do not have permission to change this password.')
        return redirect('employee-list')

    if not user:
        messages.error(request, 'This employee has no linked system account.')
        return redirect('employee-list')

    if request.method == 'POST':
        pw1 = request.POST.get('new_password1', '')
        pw2 = request.POST.get('new_password2', '')
        if not pw1 or not pw2:
            return render(request, 'orgnization/employee_change_password.html', {
                'employee': employee,
                'error': 'Please enter a new password.',
            })
        if pw1 != pw2:
            return render(request, 'orgnization/employee_change_password.html', {
                'employee': employee,
                'error': 'Passwords do not match.',
            })
        if len(pw1) < 8:
            return render(request, 'orgnization/employee_change_password.html', {
                'employee': employee,
                'error': 'Password must be at least 8 characters.',
            })

        user = employee.user
        if not user:
            return render(request, 'orgnization/employee_change_password.html', {
                'employee': employee,
                'error': 'This employee has no linked system account.',
            })

        user.set_password(pw1)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password has been updated.')
        return redirect('employee-edit', pk=employee.pk)
        return redirect('employee-edit', pk=employee.pk)

    return render(request, 'orgnization/employee_change_password.html', {
        'employee': employee,
    })
