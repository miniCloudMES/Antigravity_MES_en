from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.db.models import Count
from django.contrib import messages
from .models import Supplier, SupplierCategory
from .forms import SupplierForm, SupplierCategoryForm
from Orgnization.views import RoleRequiredMixin
import re


@login_required
def check_supplier_id(request):
    supplier_id = request.GET.get('supplier_id', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(supplier_id) < 3:
        return JsonResponse({'available': False, 'message': 'Supplier ID must be at least 3 characters.'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', supplier_id):
        return JsonResponse({'available': False, 'message': 'Cannot contain special characters.'})

    qs = Supplier.objects.filter(supplier_id=supplier_id)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This Supplier ID already exists.'})
    return JsonResponse({'available': True, 'message': 'This Supplier ID is available.'})


class SupplierDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'supplier/supplier_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_suppliers'] = Supplier.objects.count()
        ctx['active_suppliers'] = Supplier.objects.filter(is_active=True).count()
        ctx['total_categories'] = SupplierCategory.objects.count()
        ctx['recent_suppliers'] = Supplier.objects.order_by('-created_at')[:5]
        return ctx


# ── Category ──────────────────────────────────────────────────────────────────

class SupplierCategoryListView(LoginRequiredMixin, ListView):
    model = SupplierCategory
    template_name = 'supplier/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return SupplierCategory.objects.prefetch_related('suppliers').annotate(
            sup_count=Count('suppliers'),
        )


class SupplierCategoryCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'manager']
    model = SupplierCategory
    form_class = SupplierCategoryForm
    template_name = 'supplier/category_form.html'
    success_url = reverse_lazy('supplier-category-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Supplier category "{self.object.name}" has been created.')
        return response


class SupplierCategoryUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = ['admin', 'manager']
    model = SupplierCategory
    form_class = SupplierCategoryForm
    template_name = 'supplier/category_form.html'
    success_url = reverse_lazy('supplier-category-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Supplier category "{self.object.name}" has been updated.')
        return response


class SupplierCategoryDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = ['admin', 'manager']
    model = SupplierCategory
    template_name = 'supplier/category_confirm_delete.html'
    success_url = reverse_lazy('supplier-category-list')

    def form_valid(self, form):
        messages.success(self.request, f'Supplier category "{self.object.name}" has been deleted.')
        return super().form_valid(form)


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'supplier/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 15

    def get_queryset(self):
        qs = Supplier.objects.select_related('category').annotate(
            mat_count=Count('materials'),
            eq_count=Count('equipments'),
        )
        search = self.request.GET.get('search', '').strip()
        category = self.request.GET.get('category', '')
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(supplier_id__icontains=search)
        if category:
            qs = qs.filter(category_id=category)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('search', '')
        ctx['categories'] = SupplierCategory.objects.all()
        ctx['selected_category'] = self.request.GET.get('category', '')
        return ctx


class SupplierCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'supplier/supplier_form.html'
    success_url = reverse_lazy('supplier-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Supplier "{self.object.name}" has been created.')
        return response


class SupplierUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'supplier/supplier_form.html'
    success_url = reverse_lazy('supplier-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Supplier "{self.object.name}" has been updated.')
        return response


class SupplierDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'supplier/supplier_confirm_delete.html'
    success_url = reverse_lazy('supplier-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Supplier "{self.object.name}" has been deleted.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['mat_count'] = self.object.materials.count()
        ctx['eq_count'] = self.object.equipments.count()
        return ctx
