from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models, transaction
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from .models import WorkOrder, BOM, ProcessStep, WorkOrderStep, MaterialPickingItem
from .forms import WorkOrderForm, BOMForm, BOMItemFormSet, ProcessStepFormSet, WorkOrderStepFormSet, WorkOrderStepQuantityForm, WorkOrderStepTrackInForm
from Material.models import Material, StockTransaction
from Product.models import Product, ProductStockTransaction
from Orgnization.views import RoleRequiredMixin
import qrcode
from io import BytesIO
from decimal import Decimal
import re


class ProductionDashboardView(LoginRequiredMixin, TemplateView):
    """
    Production management dashboard view
    """
    template_name = 'production/production_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_workorders'] = WorkOrder.objects.count()
        context['pending_workorders'] = WorkOrder.objects.filter(status='PENDING').count()
        context['in_progress_workorders'] = WorkOrder.objects.filter(status='IN_PROGRESS').count()
        context['completed_workorders'] = WorkOrder.objects.filter(status='COMPLETED').count()
        context['abnormal_workorders'] = WorkOrder.objects.filter(status='ABNORMAL').count()
        context['total_boms'] = BOM.objects.count()
        context['active_boms'] = BOM.objects.filter(is_active=True).count()
        context['process_card_count'] = ProcessStep.objects.values('product').distinct().count()
        return context


class WorkOrderListView(LoginRequiredMixin, ListView):
    model = WorkOrder
    template_name = 'production/workorder_list.html'
    context_object_name = 'workorders'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related('product')
        status = self.request.GET.get('status')
        if status in ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'ABNORMAL'):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['status_counts'] = {
            'PENDING': WorkOrder.objects.filter(status='PENDING').count(),
            'IN_PROGRESS': WorkOrder.objects.filter(status='IN_PROGRESS').count(),
            'COMPLETED': WorkOrder.objects.filter(status='COMPLETED').count(),
            'CANCELLED': WorkOrder.objects.filter(status='CANCELLED').count(),
            'ABNORMAL': WorkOrder.objects.filter(status='ABNORMAL').count(),
        }
        return ctx


class WorkOrderCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'production/workorder_form.html'
    success_url = reverse_lazy('workorder-list')
    allowed_roles = ['admin', 'manager']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Add Work Order'
        return context

    def form_valid(self, form):
        """After saving the work order: create the picking first step (generate a material confirmation list from the BOM), then snapshot the steps from the standard process"""
        with transaction.atomic():
            self.object = form.save()

            # ── Picking station (first step, step 0) ── Generate material confirmation list from active BOM
            bom = BOM.objects.filter(product=self.object.product, is_active=True).first()
            picking_created = False
            if bom:
                WorkOrderStep.objects.create(
                    work_order=self.object,
                    source_step=None,
                    step_number=0,
                    name='Picking',
                    description='Pick materials per BOM and confirm quantities; the next step can only be entered after confirmation is completed',
                    status='PENDING',
                    is_picking_step=True,
                )
                for item in bom.items.select_related('component'):
                    MaterialPickingItem.objects.create(
                        work_order=self.object,
                        material=item.component,
                        required_quantity=item.quantity * self.object.quantity,
                    )
                picking_created = True

            # ── Standard Process step snapshot ──
            source_steps = ProcessStep.objects.filter(product=self.object.product)
            if source_steps.exists():
                for idx, src in enumerate(source_steps):
                    step = WorkOrderStep.objects.create(
                        work_order=self.object,
                        source_step=src,
                        step_number=src.step_number,
                        name=src.name,
                        description=src.description,
                        personnel_requirement=src.personnel_requirement,
                        personnel=src.personnel,
                        equipment=src.equipment,
                        material=src.material,
                        document=src.document,
                        qc_requirements=src.qc_requirements,
                        standard_time_minutes=src.standard_time_minutes,
                        status='PENDING',
                    )
                    # Auto-fill the first process step with the work order quantity
                    if idx == 0:
                        step.received_quantity = self.object.quantity
                        step.save(update_fields=['received_quantity'])
                messages.success(
                    self.request,
                    f'Work order created and {source_steps.count()} step(s) were loaded from the standard process of "{self.object.product.name}". The first process step was pre-filled with received quantity {self.object.quantity}.',
                )
            if picking_created:
                messages.success(
                    self.request,
                    f'Created the "Picking" first step with {bom.items.count()} material confirmation item(s) from the BOM (required quantities computed from work order quantity {self.object.quantity}).',
                )
        return redirect(self.success_url)


class WorkOrderUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'production/workorder_form.html'
    success_url = reverse_lazy('workorder-list')
    allowed_roles = ['admin', 'manager']

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.status == 'COMPLETED':
            messages.error(request, f'Work order "{obj.order_number}" is completed and cannot be modified.')
            return redirect('workorder-detail', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Work Order「{self.object.order_number}" has been updated.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'EditWork Order'
        return context


class WorkOrderDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = WorkOrder
    template_name = 'production/workorder_confirm_delete.html'
    success_url = reverse_lazy('workorder-list')
    allowed_roles = ['admin', 'manager']

    def form_valid(self, form):
        messages.success(self.request, f'Work Order「{self.object.order_number}" has been deleted.')
        return super().form_valid(form)


class WorkOrderDetailView(LoginRequiredMixin, DetailView):
    model = WorkOrder
    template_name = 'production/workorder_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['steps'] = self.object.steps.select_related(
            'equipment', 'material', 'document', 'personnel',
            'actual_equipment', 'track_in_by__employee', 'track_out_by__employee',
        )
        pick_items = self.object.picking_items.all()
        context['picking_total'] = pick_items.count()
        context['picking_confirmed'] = pick_items.exclude(confirmed_at__isnull=True).count()
        return context


# ── BOM Views ────────────────────────────────────────────────────────────────

class BOMListView(LoginRequiredMixin, ListView):
    model = BOM
    template_name = 'production/bom_list.html'
    context_object_name = 'boms'
    paginate_by = 15


class BOMDetailView(LoginRequiredMixin, DetailView):
    model = BOM
    template_name = 'production/bom_detail.html'
    context_object_name = 'bom'


class BOMCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = BOM
    form_class = BOMForm
    template_name = 'production/bom_form.html'
    success_url = reverse_lazy('bom-list')
    allowed_roles = ['admin', 'manager']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Add BOM'
        if self.request.POST:
            context['formset'] = BOMItemFormSet(self.request.POST)
        else:
            context['formset'] = BOMItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f'BOM for "{self.object.product.name}" has been created.')
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))


class BOMUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = ['admin', 'manager']
    model = BOM
    form_class = BOMForm
    template_name = 'production/bom_form.html'
    success_url = reverse_lazy('bom-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Edit BOM'
        if self.request.POST:
            context['formset'] = BOMItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = BOMItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f'BOM for "{self.object.product.name}" has been updated.')
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))


class BOMDeleteView(LoginRequiredMixin, DeleteView):
    model = BOM
    template_name = 'production/bom_confirm_delete.html'
    success_url = reverse_lazy('bom-list')

    def form_valid(self, form):
        messages.success(self.request, 'BOM has been deleted.')
        return super().form_valid(form)


# ── Process Card (Standard Process) Views ──────────────────────────────────────────────

class ProcessCardListView(LoginRequiredMixin, ListView):
    """List all products, marking whether a standard process is defined"""
    model = Product
    template_name = 'production/process_card_list.html'
    context_object_name = 'products'
    paginate_by = 15

    def get_queryset(self):
        qs = Product.objects.prefetch_related('process_steps').annotate(
            step_count=models.Count('process_steps'),
        ).order_by('product_id')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(product_id__icontains=q)
        return qs


class ProcessCardDetailView(LoginRequiredMixin, DetailView):
    """Process card for a single product (including all steps)"""
    model = Product
    template_name = 'production/process_card_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['steps'] = self.object.process_steps.select_related('equipment', 'material', 'document', 'personnel')
        return context


class ProcessCardEditView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Edit a product's process card (steps managed via formset)"""
    model = Product
    template_name = 'production/process_card_form.html'
    context_object_name = 'product'
    allowed_roles = ['admin', 'manager']

    fields = []  # Product fields need no editing here; only the step formset is edited

    def get_success_url(self):
        return reverse_lazy('process-card-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ProcessStepFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = ProcessStepFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save(commit=False)
            self.object.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f'Process card for "{self.object.name}" has been updated.')
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


# ── AJAX helpers ─────────────────────────────────────────────────────────────

def _check_bom_stock(order):
    """Check whether the work order BOM component stock is sufficient; return a shortage list"""
    bom = BOM.objects.filter(product=order.product, is_active=True).first()
    shortage = []
    if bom:
        for item in bom.items.select_related('component'):
            need = item.quantity * order.quantity
            if item.component.stock_quantity < need:
                shortage.append((item.component, need, item.component.stock_quantity))
    return shortage


def _deduct_bom_stock(order, user):
    """When all work order steps are completed: deduct BOM component stock (prevent double deduction; skip if already deducted by picking confirmation) and automatically add finished-goods stock"""
    # ── Material deduction (skip if picking confirmation already created an OUTBOUND, to avoid double deduction) ──
    if not StockTransaction.objects.filter(reference=order.order_number, type='OUTBOUND').exists():
        shortage = _check_bom_stock(order)
        if shortage:
            msg = 'Insufficient stock to complete the work order:'
            for mat, need, stock in shortage:
                msg += f' {mat.material_id}({mat.name}) needs {need}, available {stock};'
            return msg
        with transaction.atomic():
            bom = BOM.objects.filter(product=order.product, is_active=True).first()
            if bom:
                for item in bom.items.select_related('component'):
                    need = item.quantity * order.quantity
                    mat = item.component
                    mat.stock_quantity -= need
                    mat.save()
                    StockTransaction.objects.create(
                        material=mat,
                        type='OUTBOUND',
                        quantity=need,
                        balance_after=mat.stock_quantity,
                        reference=order.order_number,
                        remark=f'Production picking: {order.order_number} ({order.product.name} × {order.quantity})',
                        created_by=user,
                    )

    # ── Finished-goods inbound (each guarded against duplicates) ──
    with transaction.atomic():
        # Finished-goods material inbound: if a Material shares the same product_id as the finished product
        product_mat = Material.objects.filter(material_id=order.product.product_id).first()
        if product_mat and not StockTransaction.objects.filter(
            reference=order.order_number, type='INBOUND', remark__startswith='Production complete'
        ).exists():
            product_mat.stock_quantity += order.quantity
            product_mat.save()
            StockTransaction.objects.create(
                material=product_mat,
                type='INBOUND',
                quantity=order.quantity,
                balance_after=product_mat.stock_quantity,
                reference=order.order_number,
                remark=f'Production complete auto-inbound: {order.order_number} ({order.product.name} × {order.quantity})',
                created_by=user,
            )
        # Finished product's own stock auto-inbound (Product stock control), guarded against duplicates
        prod = order.product
        if not ProductStockTransaction.objects.filter(reference=order.order_number, type='INBOUND').exists():
            prod.stock_quantity = (prod.stock_quantity or 0) + order.quantity
            prod.save()
            ProductStockTransaction.objects.create(
                product=prod,
                type='INBOUND',
                quantity=order.quantity,
                balance_after=prod.stock_quantity,
                reference=order.order_number,
                remark=f'Production complete auto-inbound: {order.order_number} ({prod.name} × {order.quantity})',
                created_by=user,
            )
    return None


@login_required
@require_POST
def workorder_step_update(request, pk):
    """Update a work order step status — only Abnormal / Cancelled / review-abnormal.
    Use the dedicated endpoints workorder_step_track_in / workorder_step_track_out for Track In / Track Out.
    """
    step = get_object_or_404(WorkOrderStep, pk=pk)
    emp = getattr(request.user, 'employee', None)
    if emp is None:
        messages.error(request, 'No valid employee identity; cannot update step status.')
        return redirect('workorder-detail', pk=step.work_order.pk)

    new_status = request.POST.get('status', '')
    if new_status not in dict(WorkOrderStep.STATUS_CHOICES):
        messages.error(request, 'Invalid step status.')
        return redirect('workorder-detail', pk=step.work_order.pk)

    current = step.status
    # Allowed status transitions (track in/out are handled by dedicated endpoints)
    allowed_transitions = {
        'PENDING': {'CANCELLED'},                       # Pending → Cancelled
        'IN_PROGRESS': {'ABNORMAL', 'CANCELLED'},       # In Progress → Abnormal / Cancelled
        'ABNORMAL': {'CANCELLED'},                      # Abnormal → Cancelled (resume via Track In, leave via Track Out)
        'COMPLETED': {'ABNORMAL'},                      # Completed → Abnormal (issue found on review)
        'CANCELLED': set(),                             # Cancelled is a terminal state
    }
    if new_status == current:
        messages.info(request, f'Step "{step.name}" is already in this status.')
    elif new_status in allowed_transitions.get(current, set()):
        step.status = new_status
        step.save(update_fields=['status'])
        messages.success(request, f'Step "{step.name}" status updated to {step.get_status_display()}.')
        step.work_order.refresh_status_from_steps()
        messages.info(request, f'Work order status auto-updated to "{step.work_order.get_status_display()}".')
    else:
        messages.error(
            request,
            f'Step "{step.name}" is currently "{step.get_status_display()}" and cannot be changed to "{dict(WorkOrderStep.STATUS_CHOICES)[new_status]}".',
        )
    return redirect('workorder-detail', pk=step.work_order.pk)


# ── Track In / Track Out ──────────────────────────────────────────────────────

def _serial_prev_step(step):
    """Strict serial flow: the previous step of the current step (skipping cancelled steps), or None"""
    return step.work_order.steps.filter(
        step_number__lt=step.step_number,
    ).exclude(status='CANCELLED').order_by('-step_number').first()


@login_required
def workorder_step_track_in(request, pk):
    """Track In: enter the received quantity and a track-in note/condition.
    GET shows the track-in form; POST validates strict serial flow / personnel position / equipment status / BOM readiness,
    then records received quantity, remarks, operator, actual equipment and actual start time; status → IN_PROGRESS"""
    step = get_object_or_404(WorkOrderStep, pk=pk)
    emp = getattr(request.user, 'employee', None)
    if emp is None:
        messages.error(request, 'No valid employee identity; cannot track in.')
        return redirect('workorder-detail', pk=step.work_order.pk)

    if request.method == 'POST':
        if step.status not in ('PENDING', 'ABNORMAL'):
            messages.error(request, f'Step "{step.name}" is currently "{step.get_status_display()}" and cannot be tracked in.')
            return redirect('workorder-detail', pk=step.work_order.pk)

        # Strict serial flow: the previous step (not cancelled) must have been tracked out
        prev = _serial_prev_step(step)
        if prev and prev.status != 'COMPLETED':
            messages.error(
                request,
                f'Strict serial flow: previous step "{prev.name}" has not been tracked out (currently "{prev.get_status_display()}"), so "{step.name}" cannot be tracked in.',
            )
            return redirect('workorder-detail', pk=step.work_order.pk)

        # Personnel position match check (operator only)
        if step.personnel and emp.role == 'operator':
            if emp.position != step.personnel:
                messages.error(
                    request,
                    f'Operator position "{emp.position.name if emp.position else "none"}" does not match the required position "{step.personnel.name}".'
                )
                return redirect('workorder-detail', pk=step.work_order.pk)

        # Equipment status guard (non-active equipment blocks track in)
        if step.equipment and step.equipment.status != 'active':
            messages.error(
                request,
                f'Associated equipment "{step.equipment.name}" is currently "{step.equipment.get_status_display()}" (not active) and cannot be tracked in.'
            )
            return redirect('workorder-detail', pk=step.work_order.pk)

        # Start-up readiness check (work order not yet started)
        if step.work_order.status == 'PENDING':
            shortage = _check_bom_stock(step.work_order)
            if shortage:
                msg = 'Start-up readiness check failed; insufficient stock to track in:'
                for mat, need, stock in shortage:
                    msg += f' {mat.material_id}({mat.name}) needs {need}, available {stock};'
                messages.error(request, msg)
                return redirect('workorder-detail', pk=step.work_order.pk)

        # Received quantity + track-in note/condition
        form = WorkOrderStepTrackInForm(request.POST, instance=step)
        if not form.is_valid():
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f'Track-in data error: {e}')
            return redirect('workorder-step-track-in', pk=step.pk)
        form.save()

        now = timezone.now()
        step.status = 'IN_PROGRESS'
        step.actual_start_date = now
        step.track_in_by = request.user
        if step.actual_equipment is None:
            step.actual_equipment = step.equipment  # snapshot the planned equipment when no actual equipment is specified
        step.save(update_fields=['status', 'actual_start_date', 'track_in_by', 'actual_equipment'])

        if not step.work_order.actual_start_date:
            step.work_order.actual_start_date = now
            step.work_order.save(update_fields=['actual_start_date'])

        step.work_order.refresh_status_from_steps()
        msg = f'Step "{step.name}" has been tracked in.'
        if step.track_in_note:
            msg += f' Track-in note: {step.track_in_note}'
        messages.success(request, msg)
        return redirect('workorder-detail', pk=step.work_order.pk)

    # GET: show the track-in form (with the previous station's transferred quantity hint)
    form = WorkOrderStepTrackInForm(instance=step)
    return render(request, 'production/workorder_step_track_in.html', {
        'step': step,
        'form': form,
        'prev_step': _serial_prev_step(step),
    })


@login_required
@require_POST
def workorder_step_track_out(request, pk):
    """Track Out: require received/good/defect/loss quantities and balance before leaving,
    record the track-out operator and actual end time, set status → COMPLETED, auto-flow to the next step and deduct stock on completion"""
    step = get_object_or_404(WorkOrderStep, pk=pk)
    action = request.POST.get('action', 'trackout')

    form = WorkOrderStepQuantityForm(request.POST, instance=step)
    if not form.is_valid():
        for field, errors in form.errors.items():
            for e in errors:
                messages.error(request, f'Quantity entry error: {e}')
        return redirect('workorder-step-quantity', pk=step.pk)
    obj = form.save()  # Always save quantities first so user input is not lost

    if action == 'save':
        msg = f'Quantities for step "{obj.name}" have been saved.'
        if obj.track_out_note:
            msg += f' Track-out note: {obj.track_out_note}'
        messages.success(request, msg)
        return redirect('workorder-step-quantity', pk=step.pk)

    # ── Track Out ──
    emp = getattr(request.user, 'employee', None)
    if emp is None:
        messages.error(request, 'No valid employee identity; cannot track out.')
        return redirect('workorder-step-quantity', pk=step.pk)

    if step.status not in ('IN_PROGRESS', 'ABNORMAL'):
        messages.error(request, f'Step "{step.name}" is currently "{step.get_status_display()}" and cannot be tracked out.')
        return redirect('workorder-detail', pk=step.work_order.pk)

    # Enforce quantity balance check
    if obj.received_quantity is None:
        messages.error(request, 'You must enter the received quantity before tracking out.')
        return redirect('workorder-step-quantity', pk=step.pk)
    if not obj.balance_ok():
        messages.error(
            request,
            f'Quantities are unbalanced and cannot be tracked out: received {obj.received_quantity}, but good+defect+loss = {(obj.good_quantity or 0)+(obj.defect_quantity or 0)+(obj.loss_quantity or 0)}. Please verify the quantities before tracking out.',
        )
        return redirect('workorder-step-quantity', pk=step.pk)

    now = timezone.now()
    step.actual_end_date = now
    step.status = 'COMPLETED'
    step.track_out_by = request.user
    step.save(update_fields=['actual_end_date', 'status', 'track_out_by'])

    # Auto-flow quantities to the next step (skip cancelled steps; only fill if the next step has not been tracked in, to avoid overwriting an in-progress station)
    if step.passed_quantity:
        next_step = step.work_order.steps.filter(
            step_number__gt=step.step_number,
        ).exclude(status='CANCELLED').order_by('step_number').first()
        if next_step and next_step.status == 'PENDING':
            next_step.received_quantity = step.passed_quantity
            next_step.good_quantity = step.good_quantity
            next_step.defect_quantity = step.defect_quantity
            next_step.save(update_fields=['received_quantity', 'good_quantity', 'defect_quantity'])
            messages.success(
                request,
                f'Next step "{next_step.name}" auto-filled: received {step.passed_quantity} (good {step.good_quantity or 0}, defect {step.defect_quantity or 0}).',
            )

    # Derive the overall work order status
    wo_status = step.work_order.refresh_status_from_steps()
    msg = f'Step "{step.name}" has been tracked out; work order status auto-updated to "{step.work_order.get_status_display()}".'
    if step.track_out_note:
        msg += f' Track-out note: {step.track_out_note}'
    messages.info(request, msg)

    # All work order steps completed → check stock and deduct
    if wo_status == 'COMPLETED':
        err = _deduct_bom_stock(step.work_order, request.user)
        if err:
            messages.error(request, err)
        else:
            step.work_order.actual_end_date = timezone.now()
            step.work_order.save(update_fields=['actual_end_date'])
            messages.success(request, f'Work order {step.work_order.order_number} completed; BOM component stock deducted and finished goods auto-inbound.')
    return redirect('workorder-detail', pk=step.work_order.pk)


# ── Picking Confirmation (First Station) ────────────────────────────────────────────────────────

@login_required
def workorder_picking(request, pk):
    """Picking station confirmation: show each material's required quantity per BOM; the next step can only be entered after the operator confirms the quantities"""
    wo = get_object_or_404(WorkOrder, pk=pk)
    emp = getattr(request.user, 'employee', None)
    if emp is None:
        messages.error(request, 'No valid employee identity; cannot confirm picking.')
        return redirect('workorder-detail', pk=wo.pk)

    picking_step = wo.steps.filter(is_picking_step=True).first()
    items = wo.picking_items.select_related('material').all()

    if request.method == 'POST':
        if not picking_step or picking_step.status != 'PENDING':
            messages.error(request, 'The picking station cannot be confirmed right now.')
            return redirect('workorder-detail', pk=wo.pk)

        # 1. Parse and validate each confirmed quantity (format / non-negative / cannot exceed current stock)
        parsed = []
        errors = []
        for item in items:
            raw = request.POST.get(f'qty_{item.pk}', '').strip()
            try:
                qty = Decimal(raw) if raw else item.required_quantity
                if qty < 0:
                    raise ValueError('negative')
            except Exception:
                errors.append(f'"{item.material.material_id}" confirmed quantity has an invalid format')
                continue
            if qty > item.material.stock_quantity:
                errors.append(
                    f'"{item.material.material_id}" confirmed quantity {qty} exceeds current stock {item.material.stock_quantity}; cannot pick.'
                )
                continue
            parsed.append((item, qty))

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('workorder-picking', pk=wo.pk)

        # 2. Save the confirmation data
        shortage = False
        for item, qty in parsed:
            item.confirmed_quantity = qty
            item.confirmed_by = request.user
            item.confirmed_at = timezone.now()
            item.note = request.POST.get(f'note_{item.pk}', '').strip()[:255]
            item.save()
            if qty < item.required_quantity:
                shortage = True

        # 3. Complete the picking station + directly deduct stock (same transaction, prevents double deduction)
        with transaction.atomic():
            already_deducted = StockTransaction.objects.filter(
                reference=wo.order_number, type='OUTBOUND', remark__startswith='Picking confirmation'
            ).exists()
            if not already_deducted:
                for item, qty in parsed:
                    if qty <= 0:
                        continue
                    mat = item.material
                    mat.stock_quantity = mat.stock_quantity - qty
                    mat.save()
                    StockTransaction.objects.create(
                        material=mat,
                        type='OUTBOUND',
                        quantity=qty,
                        balance_after=mat.stock_quantity,
                        reference=wo.order_number,
                        remark=f'Picking confirmation: {wo.order_number} ({wo.product.name} × {qty} {mat.unit})',
                        created_by=request.user,
                    )

            now = timezone.now()
            picking_step.status = 'COMPLETED'
            picking_step.actual_start_date = picking_step.actual_start_date or now
            picking_step.actual_end_date = now
            picking_step.track_in_by = picking_step.track_in_by or request.user
            picking_step.track_out_by = request.user
            picking_step.save(update_fields=[
                'status', 'actual_start_date', 'actual_end_date', 'track_in_by', 'track_out_by',
            ])
            wo.refresh_status_from_steps()

        msg = 'Picking confirmed; stock has been deducted directly. You may proceed to the next step.'
        if shortage:
            msg += ' (Note: some materials were confirmed below the required quantity; please watch for shortages)'
        messages.success(request, msg)
        return redirect('workorder-detail', pk=wo.pk)

    return render(request, 'production/workorder_picking.html', {
        'work_order': wo,
        'items': items,
        'picking_step': picking_step,
    })


# ── Step Quantity Entry ───────────────────────────────────────────────────────────────────────

@login_required
def workorder_step_quantity(request, pk):
    step = get_object_or_404(WorkOrderStep, pk=pk)
    if request.method == 'POST':
        form = WorkOrderStepQuantityForm(request.POST, instance=step)
        if form.is_valid():
            obj = form.save()
            if obj.balance_ok():
                messages.success(request, f'Quantities for step "{obj.name}" have been updated.')
            else:
                messages.warning(
                    request,
                    f'Quantities for step "{obj.name}" saved but not yet balanced: received {obj.received_quantity}, good+defect+loss = {(obj.good_quantity or 0)+(obj.defect_quantity or 0)+(obj.loss_quantity or 0)}.',
                )
            return redirect('workorder-detail', pk=step.work_order.pk)
    else:
        form = WorkOrderStepQuantityForm(instance=step)
    return render(request, 'production/workorder_step_quantity.html', {
        'step': step,
        'form': form,
        'trackout_mode': request.GET.get('action') == 'trackout',
    })


class ProductionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'production/production_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = WorkOrderStep.objects.exclude(received_quantity__isnull=True)
        total_received = sum((s.received_quantity or 0) for s in qs)
        total_good = sum((s.good_quantity or 0) for s in qs)
        total_defect = sum((s.defect_quantity or 0) for s in qs)
        total_loss = sum((s.loss_quantity or 0) for s in qs)
        context['steps'] = qs.select_related('work_order__product', 'personnel').order_by('work_order__order_number', 'step_number')
        context['total_received'] = total_received
        context['total_good'] = total_good
        context['total_defect'] = total_defect
        context['total_loss'] = total_loss
        context['yield_rate'] = round(total_good / total_received, 4) if total_received else 0
        return context


# ── AJAX helpers ─────────────────────────────────────────────────────────────

@login_required
def check_workorder_number(request):
    order_number = request.GET.get('order_number', '').strip()
    exclude_pk = request.GET.get('pk')
    if not order_number:
        return JsonResponse({'available': False, 'message': 'Work order number cannot be empty'})
    if not re.match(r'^[A-Za-z0-9_\-]+$', order_number):
        return JsonResponse({'available': False, 'message': 'Cannot contain special characters'})
    qs = WorkOrder.objects.filter(order_number=order_number)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        return JsonResponse({'available': False, 'message': 'This work order number already exists'})
    return JsonResponse({'available': True, 'message': 'This work order number is available'})


# ── Work Order QR-Code ─────────────────────────────────────────────────────────────

@login_required
def workorder_qrcode(request, pk):
    """Generate a work order QR-Code PNG (encoding the work order number) for printing on the shop floor"""
    wo = get_object_or_404(WorkOrder, pk=pk)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(wo.order_number)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    response = HttpResponse(buf.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="qr_{wo.order_number}.png"'
    response['Cache-Control'] = 'max-age=86400'  # QR content is static; cache for one day
    return response

