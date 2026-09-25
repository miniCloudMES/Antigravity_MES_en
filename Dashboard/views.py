from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from Material.models import Material
from Production.models import WorkOrder
from Documents.models import Document
from django.utils import timezone

DASHBOARD_TEMPLATES = ('classic', 'industrial')


class LandingPageView(TemplateView):
    template_name = 'dashboard/landing.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    login_url = '/accounts/login/'

    def _resolve_template_name(self):
        """Template selection: URL ?template= takes priority, then session preference, defaults to classic"""
        name = self.request.GET.get('template')
        if name in DASHBOARD_TEMPLATES:
            self.request.session['dashboard_template'] = name
            return name
        return self.request.session.get('dashboard_template', 'classic')

    def get_template_names(self):
        if self._resolve_template_name() == 'industrial':
            return ['dashboard/dashboard_industrial.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_dashboard_template'] = self._resolve_template_name()
        qs = WorkOrder.objects.all()
        ctx['pending_workorders'] = qs.filter(status='PENDING').count()
        ctx['in_progress_workorders'] = qs.filter(status='IN_PROGRESS').count()
        ctx['completed_workorders'] = qs.filter(status='COMPLETED').count()
        ctx['cancelled_workorders'] = qs.filter(status='CANCELLED').count()
        ctx['total_workorders'] = qs.count()
        materials = list(Material.objects.select_related('supplier').all())
        ctx['low_stock_count'] = sum(1 for m in materials if m.is_low_stock)
        ctx['total_materials'] = len(materials)
        ctx['low_stock_materials'] = [m for m in materials if m.is_low_stock][:6]
        ctx['overdue_workorders'] = qs.filter(status__in=['PENDING', 'IN_PROGRESS'], planned_end_date__lt=timezone.now()).count()
        ctx['recent_workorders'] = qs.select_related('product', 'customer').order_by('-created_at')[:5]
        doc_qs = Document.objects.all()
        ctx['draft_documents'] = doc_qs.filter(status='draft').count()
        ctx['pending_documents'] = doc_qs.filter(status='pending').count()
        ctx['approved_documents'] = doc_qs.filter(status='approved').count()
        ctx['rejected_documents'] = doc_qs.filter(status='rejected').count()
        return ctx


@login_required
@require_POST
def dashboard_template_switch(request):
    """Switch dashboard template (classic / industrial), preference saved in session"""
    name = request.POST.get('template', '')
    if name in DASHBOARD_TEMPLATES:
        request.session['dashboard_template'] = name
    return redirect('dashboard')
