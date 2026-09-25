from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Count, Sum, Q
from django.utils.dateparse import parse_date
from decimal import Decimal
from django.db import transaction
from .models import ProductCategory, Product, ProductStockTransaction
from .forms import ProductCategoryForm, ProductForm, ProductStockTransactionForm
from Production.models import WorkOrder, BOM, ProcessStep
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
def check_product_id(request):
    product_id = request.GET.get('product_id', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(product_id) < 3:
        return JsonResponse({'available': False, 'message': 'Product ID requires at least 3 characters'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', product_id):
        return JsonResponse({'available': False, 'message': 'Cannot contain special characters'})

    qs = Product.objects.filter(product_id=product_id)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This ID already exists, please use another'})
    return JsonResponse({'available': True, 'message': 'This ID is available'})


class ProductDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'product/product_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_products'] = Product.objects.count()
        ctx['total_categories'] = ProductCategory.objects.count()
        ctx['active_products'] = Product.objects.filter(is_active=True).count()
        ctx['with_bom_count'] = BOM.objects.values('product').distinct().count()
        ctx['with_process_count'] = ProcessStep.objects.values('product').distinct().count()
        ctx['low_stock_count'] = sum(1 for p in Product.objects.all() if p.is_low_stock)
        ctx['low_stock_products'] = [p for p in Product.objects.select_related('category').all() if p.is_low_stock][:20]
        ctx['recent_products'] = Product.objects.order_by('-created_at')[:5]
        return ctx


# ── Category ──────────────────────────────────────────────────────────────────

class ProductCategoryListView(LoginRequiredMixin, ListView):
    model = ProductCategory
    template_name = 'product/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return ProductCategory.objects.prefetch_related('products')


class ProductCategoryCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'manager']
    model = ProductCategory
    form_class = ProductCategoryForm
    template_name = 'product/category_form.html'
    success_url = reverse_lazy('product-category-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Product category "{self.object.name}" has been created.')
        return response


class ProductCategoryUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = ['admin', 'manager']
    model = ProductCategory
    form_class = ProductCategoryForm
    template_name = 'product/category_form.html'
    success_url = reverse_lazy('product-category-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Product category "{self.object.name}" has been updated.')
        return response


class ProductCategoryDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = ['admin', 'manager']
    model = ProductCategory
    template_name = 'product/category_confirm_delete.html'
    success_url = reverse_lazy('product-category-list')

    def form_valid(self, form):
        messages.success(self.request, f'Product category "{self.object.name}" has been deleted.')
        return super().form_valid(form)


# ── Product ──────────────────────────────────────────────────────────────────

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'product/product_list.html'
    context_object_name = 'products'
    paginate_by = 15

    def get_queryset(self):
        qs = Product.objects.select_related('category').annotate(
            bom_count=Count('bom'),
            workorder_count=Count('workorder'),
        ).order_by('product_id')
        category = self.request.GET.get('category')
        search = self.request.GET.get('search', '').strip()
        if category:
            qs = qs.filter(category_id=category)
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(product_id__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = ProductCategory.objects.all()
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['search'] = self.request.GET.get('search', '')
        return ctx


class ProductCreateView(CroppedImageMixin, LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'product/product_form.html'
    success_url = reverse_lazy('product-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Product "{self.object.name}" has been created.')
        return response


class ProductUpdateView(CroppedImageMixin, LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'product/product_form.html'
    success_url = reverse_lazy('product-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Product "{self.object.name}" has been updated.')
        return response


class ProductDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Product
    template_name = 'product/product_confirm_delete.html'
    success_url = reverse_lazy('product-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Product "{self.object.name}" has been deleted.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['workorder_count'] = self.object.workorder.count()
        ctx['has_bom'] = hasattr(self.object, 'bom')
        return ctx
# ── Stock Transaction ─────────────────────────────────────────────────────────

class ProductStockTransactionListView(LoginRequiredMixin, ListView):
    model = ProductStockTransaction
    template_name = 'product/product_stock_transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        qs = ProductStockTransaction.objects.select_related('product', 'created_by')
        txn_type = self.request.GET.get('type')
        product_id = self.request.GET.get('product_id')
        date_from = parse_date(self.request.GET.get('date_from') or '')
        date_to = parse_date(self.request.GET.get('date_to') or '')
        exact_product = self.request.GET.get('product')
        if txn_type:
            qs = qs.filter(type=txn_type)
        if product_id:
            qs = qs.filter(product__product_id__icontains=product_id)
        if exact_product:
            qs = qs.filter(product__pk=exact_product)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['product_choices'] = Product.objects.all()
        ctx['type_choices'] = ProductStockTransaction.TRANSACTION_TYPES
        ctx['selected_type'] = self.request.GET.get('type', '')
        ctx['selected_product'] = self.request.GET.get('product_id', '')
        ctx['selected_date_from'] = self.request.GET.get('date_from', '')
        ctx['selected_date_to'] = self.request.GET.get('date_to', '')
        # When a specific product is selected, show its name in the header
        exact_pk = self.request.GET.get('product')
        if exact_pk:
            ctx['filtered_product'] = Product.objects.filter(pk=exact_pk).first()
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


class ProductStockTransactionCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'manager']
    model = ProductStockTransaction
    form_class = ProductStockTransactionForm
    template_name = 'product/product_stock_transaction_form.html'
    success_url = reverse_lazy('product-stock-transaction-list')

    def get_initial(self):
        initial = super().get_initial()
        product_pk = self.request.GET.get('product')
        if product_pk:
            initial['product'] = product_pk
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        product_pk = self.request.GET.get('product')
        if product_pk:
            kwargs['product_instance'] = get_object_or_404(Product, pk=product_pk)
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            txn = form.save(commit=False)
            txn.created_by = self.request.user
            prod = txn.product
            if txn.type == 'INBOUND':
                prod.stock_quantity += txn.quantity
            elif txn.type == 'OUTBOUND':
                prod.stock_quantity -= txn.quantity
            elif txn.type == 'ADJUST':
                # Adjustment: quantity is the adjustment amount (positive = add stock, negative = subtract stock)
                prod.stock_quantity += txn.quantity
            txn.balance_after = prod.stock_quantity
            txn.save()
            prod.save()
        messages.success(self.request, 'Product stock transaction created and stock updated.')
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Please check input fields.')
        return super().form_invalid(form)


class ProductStockTransactionQuickCreate(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'manager']
    model = ProductStockTransaction
    form_class = ProductStockTransactionForm
    template_name = 'product/product_stock_transaction_quick_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        product_pk = self.kwargs.get('product_pk')
        if product_pk:
            kwargs['product_instance'] = get_object_or_404(Product, pk=product_pk)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product_pk = self.kwargs.get('product_pk')
        if product_pk:
            ctx['product'] = get_object_or_404(Product, pk=product_pk)
        return ctx

    def post(self, request, product_pk=None, *args, **kwargs):
        prod = get_object_or_404(Product, pk=product_pk)
        form = self.get_form_class()(request.POST, product_instance=prod)
        if form.is_valid():
            return self.form_valid(form, prod)
        return render(request, self.get_template_names()[0], {'form': form, 'product': prod})

    def form_valid(self, form, prod):
        with transaction.atomic():
            txn = form.save(commit=False)
            txn.created_by = self.request.user
            txn.product = prod
            if txn.type == 'INBOUND':
                prod.stock_quantity += txn.quantity
            elif txn.type == 'OUTBOUND':
                prod.stock_quantity -= txn.quantity
            elif txn.type == 'ADJUST':
                # Adjustment: quantity is the adjustment amount (positive = add stock, negative = subtract stock)
                prod.stock_quantity += txn.quantity
            txn.balance_after = prod.stock_quantity
            txn.save()
            prod.save()
        messages.success(self.request, 'Product stock transaction completed.')
        return redirect('product-list')