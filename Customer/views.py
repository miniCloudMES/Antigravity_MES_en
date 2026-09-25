from django.shortcuts import render
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Customer
from .forms import CustomerForm
from Orgnization.views import RoleRequiredMixin
import re


@login_required
def check_customer_id(request):
    customer_id = request.GET.get('customer_id', '').strip()
    exclude_pk = request.GET.get('pk')

    if len(customer_id) < 3:
        return JsonResponse({'available': False, 'message': 'Customer ID must be at least 3 characters.'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', customer_id):
        return JsonResponse({'available': False, 'message': 'Only alphanumeric characters, underscores, and hyphens are allowed.'})

    qs = Customer.objects.filter(customer_id=customer_id)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This Customer ID is already in use.'})
    return JsonResponse({'available': True, 'message': 'This Customer ID is available.'})


class CustomerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'customer/customer_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Customer.objects.all()
        context['total_customers'] = qs.count()
        context['active_customers'] = qs.filter(is_active=True).count()
        context['inactive_customers'] = qs.filter(is_active=False).count()
        context['recent_customers'] = qs.order_by('-created_at')[:8].count()
        context['recent_customer_list'] = qs.order_by('-created_at')[:8]
        return context


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customer/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 15


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'customer/customer_detail.html'
    context_object_name = 'customer'


class CustomerCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/customer_form.html'
    success_url = reverse_lazy('customer:customer-list')
    allowed_roles = ['admin', 'manager']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'New Customer'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Customer "{self.object.name}" has been created.')
        return response


class CustomerUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/customer_form.html'
    success_url = reverse_lazy('customer:customer-list')
    allowed_roles = ['admin', 'manager']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Edit Customer'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Customer "{self.object.name}" has been updated.')
        return response


class CustomerDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customer/customer_confirm_delete.html'
    success_url = reverse_lazy('customer:customer-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, 'Customer deleted.')
        return super().form_valid(form)
