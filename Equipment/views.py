from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.forms import ValidationError
from .models import EquipmentCategory, Equipment, MaintenanceRecord
from Orgnization.views import RoleRequiredMixin
from django.core.files.uploadedfile import InMemoryUploadedFile
import base64
import io
import uuid
import re


class CroppedImageMixin:
    """Decode base64 from Cropper.js and inject into request.FILES['image']."""

    def post(self, request, *args, **kwargs):
        b64 = request.POST.get('image_cropped', '').strip()
        if b64 and b64 != 'REMOVE':
            # Drop the "data:image/...;base64," prefix
            if ',' in b64:
                b64 = b64.split(',', 1)[1]
            img_bytes = base64.b64decode(b64)
            file_obj = InMemoryUploadedFile(
                file=io.BytesIO(img_bytes),
                field_name='image',
                name=f"{uuid.uuid4().hex}.jpg",
                content_type='image/jpeg',
                size=len(img_bytes),
                charset=None,
            )
            request.FILES['image'] = file_obj
        return super().post(request, *args, **kwargs)


@login_required
def check_equipment_id(request):
    eq_id = request.GET.get('equipment_id', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(eq_id) < 3:
        return JsonResponse({'available': False, 'message': 'Equipment ID must be at least 3 characters long.'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', eq_id):
        return JsonResponse({'available': False, 'message': 'Cannot contain special characters'})

    qs = Equipment.objects.filter(equipment_id=eq_id)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This ID already exists, please use another'})
    return JsonResponse({'available': True, 'message': 'This ID is available'})

class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['equipment_id', 'name', 'category', 'status', 'purchase_date', 'location', 'supplier', 'image', 'notes']
        widgets = {
            'equipment_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EQ-2024-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter equipment name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control date-picker', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'OtherNotes'}),
        }

class EquipmentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'equipment/equipment_dashboard.html'

class EquipmentCategoryForm(forms.ModelForm):
    class Meta:
        model = EquipmentCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class EquipmentCategoryListView(LoginRequiredMixin, ListView):
    model = EquipmentCategory
    template_name = 'equipment/category_list.html'
    context_object_name = 'categories'

class EquipmentCategoryCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = EquipmentCategory
    form_class = EquipmentCategoryForm
    template_name = 'equipment/category_form.html'
    success_url = reverse_lazy('equipment-category-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Equipment Category「{self.object.name}" has been created.')
        return response

class EquipmentCategoryUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = EquipmentCategory
    form_class = EquipmentCategoryForm
    template_name = 'equipment/category_form.html'
    success_url = reverse_lazy('equipment-category-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Equipment Category「{self.object.name}" has been updated.')
        return response

class EquipmentCategoryDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = EquipmentCategory
    template_name = 'equipment/category_confirm_delete.html'
    success_url = reverse_lazy('equipment-category-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Equipment Category「{self.object.name}" has been deleted.')
        return super().form_valid(form)

class EquipmentListView(LoginRequiredMixin, ListView):
    model = Equipment
    template_name = 'equipment/equipment_list.html'
    context_object_name = 'equipments'

    def get_queryset(self):
        # Join category/supplier in a single query to avoid per-row lookups in the list (N+1)
        return super().get_queryset().select_related('category', 'supplier')

class EquipmentCreateView(CroppedImageMixin, LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'equipment/equipment_form.html'
    success_url = reverse_lazy('equipment-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Equipment「{self.object.name}" has been created.')
        return response

class EquipmentUpdateView(CroppedImageMixin, LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'equipment/equipment_form.html'
    success_url = reverse_lazy('equipment-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Equipment「{self.object.name}" has been updated.')
        return response

class EquipmentDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Equipment
    template_name = 'equipment/equipment_confirm_delete.html'
    success_url = reverse_lazy('equipment-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Equipment「{self.object.name}" has been deleted.')
        return super().form_valid(form)


class EquipmentDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'equipment/equipment_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['equipment'] = get_object_or_404(Equipment, pk=self.kwargs['pk'])
        ctx['records'] = ctx['equipment'].maintenance_records.select_related('performed_by').all()[:20]
        return ctx


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = ['type', 'performed_by', 'start_time', 'end_time', 'remark']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'performed_by': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Maintenance description'}),
        }


class MaintenanceRecordCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = MaintenanceRecord
    form_class = MaintenanceRecordForm
    template_name = 'equipment/maintenance_form.html'
    success_url = reverse_lazy('equipment-list')
    allowed_roles = ['admin', 'manager']

    def dispatch(self, request, *args, **kwargs):
        self.equipment = get_object_or_404(Equipment, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['equipment'] = self.equipment
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        initial['performed_by'] = self.request.user.pk
        return initial

    def form_valid(self, form):
        with transaction.atomic():
            record = form.save(commit=False)
            record.equipment = self.equipment
            record.save()
        messages.success(self.request, 'Maintenance record created.')
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Please check input fields.')
        return super().form_invalid(form)
