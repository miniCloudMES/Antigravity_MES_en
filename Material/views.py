from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Sum, Q
from django.utils.dateparse import parse_date
from decimal import Decimal
from django.contrib import messages
from django.forms import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import MaterialCategory, Material, StockTransaction
from Orgnization.views import RoleRequiredMixin
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
def check_material_id(request):
    mat_id = request.GET.get('material_id', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(mat_id) < 3:
        return JsonResponse({'available': False, 'message': 'Material ID must be at least 3 characters long.'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', mat_id):
        return JsonResponse({'available': False, 'message': 'Cannot contain special characters'})

    qs = Material.objects.filter(material_id=mat_id)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This ID already exists, please use another'})
    return JsonResponse({'available': True, 'message': 'This ID is available'})


class MaterialCategoryForm(forms.ModelForm):
    class Meta:
        model = MaterialCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electronic components'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter category description'}),
        }


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['material_id', 'name', 'category', 'unit', 'image', 'min_stock', 'supplier', 'location', 'notes']
        widgets = {
            'material_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MAT-2024-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter material name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'placeholder': '0'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location (e.g. A-01-02)'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'OtherNotes'}),
        }


class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['material', 'type', 'quantity', 'reference', 'remark']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Work order / purchase order no.'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Remarks (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        self.material_instance = kwargs.pop('material_instance', None)
        super().__init__(*args, **kwargs)
        if self.material_instance:
            self.fields['material'].initial = self.material_instance
        self.fields['material'].disabled = bool(self.material_instance)
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
        mat = self.material_instance or cleaned.get('material')
        if not mat:
            return cleaned
        if txn_type == 'OUTBOUND' and mat.stock_quantity < qty:
            raise ValidationError('Outbound quantity cannot exceed the current stock.')
        if txn_type == 'ADJUST' and qty < 0 and mat.stock_quantity + qty < 0:
            raise ValidationError('Stock after adjustment cannot be negative.')
        return cleaned


class MaterialDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'material/material_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_materials'] = Material.objects.count()
        ctx['total_categories'] = MaterialCategory.objects.count()
        ctx['low_stock_count'] = sum(1 for m in Material.objects.all() if m.is_low_stock)
        ctx['low_stock_materials'] = [m for m in Material.objects.select_related('category').all() if m.is_low_stock][:20]
        return ctx


# ── Category ──────────────────────────────────────────────────────────────────

class MaterialCategoryListView(LoginRequiredMixin, ListView):
    model = MaterialCategory
    template_name = 'material/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return MaterialCategory.objects.prefetch_related('materials')


class MaterialCategoryCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'manager']
    model = MaterialCategory
    form_class = MaterialCategoryForm
    template_name = 'material/category_form.html'
    success_url = reverse_lazy('material-category-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Material Category「{self.object.name}" has been created.')
        return response


class MaterialCategoryUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = ['admin', 'manager']
    model = MaterialCategory
    form_class = MaterialCategoryForm
    template_name = 'material/category_form.html'
    success_url = reverse_lazy('material-category-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Material Category「{self.object.name}" has been updated.')
        return response


class MaterialCategoryDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = ['admin', 'manager']
    model = MaterialCategory
    template_name = 'material/category_confirm_delete.html'
    success_url = reverse_lazy('material-category-list')

    def form_valid(self, form):
        messages.success(self.request, f'Material Category「{self.object.name}" has been deleted.')
        return super().form_valid(form)


# ── Material ──────────────────────────────────────────────────────────────────

class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = 'material/material_list.html'
    context_object_name = 'materials'

    def get_queryset(self):
        qs = Material.objects.select_related('category')
        category = self.request.GET.get('category')
        search = self.request.GET.get('search', '').strip()
        if category:
            qs = qs.filter(category_id=category)
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(material_id__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = MaterialCategory.objects.all()
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['search'] = self.request.GET.get('search', '')
        return ctx


class MaterialCreateView(CroppedImageMixin, LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Material
    form_class = MaterialForm
    template_name = 'material/material_form.html'
    success_url = reverse_lazy('material-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Material「{self.object.name}" has been created.')
        return response


class MaterialUpdateView(CroppedImageMixin, LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Material
    form_class = MaterialForm
    template_name = 'material/material_form.html'
    success_url = reverse_lazy('material-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Material「{self.object.name}" has been updated.')
        return response


class MaterialDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Material
    template_name = 'material/material_confirm_delete.html'
    success_url = reverse_lazy('material-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Material「{self.object.name}" has been deleted.')
        return super().form_valid(form)


# ── Stock Transaction ─────────────────────────────────────────────────────────

class StockTransactionListView(LoginRequiredMixin, ListView):
    model = StockTransaction
    template_name = 'material/stock_transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        qs = StockTransaction.objects.select_related('material', 'created_by')
        txn_type = self.request.GET.get('type')
        material_id = self.request.GET.get('material_id')
        date_from = parse_date(self.request.GET.get('date_from') or '')
        date_to = parse_date(self.request.GET.get('date_to') or '')
        exact_material = self.request.GET.get('material')
        if txn_type:
            qs = qs.filter(type=txn_type)
        if material_id:
            qs = qs.filter(material__material_id__icontains=material_id)
        if exact_material:
            qs = qs.filter(material__pk=exact_material)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['material_choices'] = Material.objects.all()
        ctx['type_choices'] = StockTransaction.TRANSACTION_TYPES
        ctx['selected_type'] = self.request.GET.get('type', '')
        ctx['selected_material'] = self.request.GET.get('material_id', '')
        ctx['selected_date_from'] = self.request.GET.get('date_from', '')
        ctx['selected_date_to'] = self.request.GET.get('date_to', '')
        # When a single material is selected, expose its name for the page header
        exact_pk = self.request.GET.get('material')
        if exact_pk:
            ctx['filtered_material'] = Material.objects.filter(pk=exact_pk).first()
        # Period transaction totals (based on filtered results, unaffected by pagination)
        totals = self.get_queryset().aggregate(
            inbound=Sum('quantity', filter=Q(type='INBOUND')),
            outbound=Sum('quantity', filter=Q(type='OUTBOUND')),
            adjust=Sum('quantity', filter=Q(type='ADJUST')),
        )
        ctx['summary_inbound'] = totals['inbound'] or Decimal('0')
        ctx['summary_outbound'] = totals['outbound'] or Decimal('0')
        ctx['summary_adjust'] = totals['adjust'] or Decimal('0')
        ctx['summary_count'] = self.get_queryset().count()
        # Query string for pagination links (remove 'page' param)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['base_query'] = params.urlencode()
        return ctx


class StockTransactionCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'manager']
    model = StockTransaction
    form_class = StockTransactionForm
    template_name = 'material/stock_transaction_form.html'
    success_url = reverse_lazy('stock-transaction-list')

    def get_initial(self):
        initial = super().get_initial()
        material_pk = self.request.GET.get('material')
        if material_pk:
            initial['material'] = material_pk
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        material_pk = self.request.GET.get('material')
        if material_pk:
            kwargs['material_instance'] = get_object_or_404(Material, pk=material_pk)
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            txn = form.save(commit=False)
            txn.created_by = self.request.user
            mat = txn.material
            if txn.type == 'INBOUND':
                mat.stock_quantity += txn.quantity
            elif txn.type == 'OUTBOUND':
                mat.stock_quantity -= txn.quantity
            elif txn.type == 'ADJUST':
                # Adjustment: quantity is the adjustment amount (positive = add stock, negative = subtract stock)
                mat.stock_quantity += txn.quantity
            txn.balance_after = mat.stock_quantity
            txn.save()
            mat.save()
        messages.success(self.request, 'Stock transaction created and stock updated.')
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Please check input fields.')
        return super().form_invalid(form)


class StockTransactionQuickCreate(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'manager']
    model = StockTransaction
    form_class = StockTransactionForm
    template_name = 'material/stock_transaction_quick_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        material_pk = self.kwargs.get('material_pk')
        if material_pk:
            kwargs['material_instance'] = get_object_or_404(Material, pk=material_pk)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        material_pk = self.kwargs.get('material_pk')
        if material_pk:
            ctx['material'] = get_object_or_404(Material, pk=material_pk)
        return ctx

    def post(self, request, material_pk=None, *args, **kwargs):
        mat = get_object_or_404(Material, pk=material_pk)
        form = self.get_form_class()(request.POST, material_instance=mat)
        if form.is_valid():
            return self.form_valid(form, mat)
        return render(request, self.get_template_names()[0], {'form': form, 'material': mat})

    def form_valid(self, form, mat):
        with transaction.atomic():
            txn = form.save(commit=False)
            txn.created_by = self.request.user
            txn.material = mat
            if txn.type == 'INBOUND':
                mat.stock_quantity += txn.quantity
            elif txn.type == 'OUTBOUND':
                mat.stock_quantity -= txn.quantity
            elif txn.type == 'ADJUST':
                # Adjustment: quantity is the adjustment amount (positive = add stock, negative = subtract stock)
                mat.stock_quantity += txn.quantity
            txn.balance_after = mat.stock_quantity
            txn.save()
            mat.save()
        messages.success(self.request, 'Stock adjustment applied.')
        return redirect('material-list')
