from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from Orgnization.models import Department, Position, Employee
from Product.models import Product, ProductCategory
from Material.models import Material, MaterialCategory, StockTransaction
from Equipment.models import Equipment, EquipmentCategory
from Production.models import WorkOrder, WorkOrderStep, BOM, BOMItem, ProcessStep, MaterialPickingItem

User = get_user_model()

class ProductionSafeguardTestCase(TestCase):
    def setUp(self):
        # 1. Organization structure
        self.dept = Department.objects.create(code='D001', name='Production Department')
        self.pos_op = Position.objects.create(code='P001', name='Operator')
        self.pos_qa = Position.objects.create(code='P002', name='QC Inspector')

        # Operator and QC Inspector accounts
        self.user_op = User.objects.create_user(username='op_user', password='password123')
        self.emp_op = Employee.objects.create(
            user=self.user_op, emp_no='EMP-001', name='Ming',
            department=self.dept, position=self.pos_op, role='operator'
        )

        self.user_mgr = User.objects.create_user(username='mgr_user', password='password123')
        self.emp_mgr = Employee.objects.create(
            user=self.user_mgr, emp_no='EMP-002', name='Manager Wang',
            department=self.dept, position=self.pos_op, role='manager'
        )

        # 2. Product and Material
        self.prod_cat = ProductCategory.objects.create(name='Finished Goods')
        self.product = Product.objects.create(
            product_id='PROD-ABC', name='Smart Watch', category=self.prod_cat, unit='pcs'
        )

        # NOTE: the name must avoid the one already created by the migration seed
        # (0003_populate_material_categories), otherwise the UNIQUE constraint fails.
        self.mat_cat = MaterialCategory.objects.create(name='Test Electronics')
        # BOM component (raw material): screen
        self.material = Material.objects.create(
            material_id='MAT-SCR', name='Watch Screen', category=self.mat_cat, unit='pcs', stock_quantity=10
        )
        # Finished-goods Material (used to verify finished-goods inbound; ID matches product_id)
        self.product_material = Material.objects.create(
            material_id='PROD-ABC', name='Smart Watch', category=self.mat_cat, unit='pcs', stock_quantity=5
        )

        # 3. BOM relation (producing 1 Smart Watch requires 1 screen)
        self.bom = BOM.objects.create(product=self.product, version='1.0', is_active=True)
        self.bom_item = BOMItem.objects.create(bom=self.bom, component=self.material, quantity=1.0)

        # 4. Equipment
        self.eq_cat = EquipmentCategory.objects.create(name='Lamination Equipment')
        self.equipment = Equipment.objects.create(
            equipment_id='EQ-001', name='Screen Lamination Machine', category=self.eq_cat, status='active'
        )

        # 5. Standard Process and Work Order
        self.proc_step = ProcessStep.objects.create(
            product=self.product, step_number=1, name='Screen Lamination',
            personnel=self.pos_qa, equipment=self.equipment, material=self.material
        )

        self.work_order = WorkOrder.objects.create(
            order_number='WO-2026082001', product=self.product, quantity=5,
            planned_start_date=timezone.now(), planned_end_date=timezone.now() + timezone.timedelta(days=1)
        )
        # Work order step snapshot
        self.wo_step = WorkOrderStep.objects.create(
            work_order=self.work_order, source_step=self.proc_step, step_number=1,
            name='Screen Lamination', personnel=self.pos_qa, equipment=self.equipment,
            material=self.material, status='PENDING'
        )

        self.client = Client()

    def test_personnel_role_verification(self):
        """Test 1: a regular operator with a mismatched position must be blocked from Track In"""
        self.client.force_login(self.user_op)
        url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})

        # op_user's position is pos_op (Operator), but the step requires pos_qa (QC Inspector)
        response = self.client.post(url, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'PENDING')  # status must stay PENDING

        # manager must not be restricted by position
        self.client.force_login(self.user_mgr)
        response = self.client.post(url, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'IN_PROGRESS')

    def test_equipment_safeguard(self):
        """Test 2: equipment status other than active blocks Track In"""
        self.equipment.status = 'broken'
        self.equipment.save()

        self.client.force_login(self.user_mgr)
        url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        response = self.client.post(url, follow=True)

        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'PENDING')  # must be blocked and stay PENDING

    def test_shortage_precheck_and_inbound(self):
        """Test 3 & 4: BOM readiness check and automatic finished-goods inbound on completion"""
        self.client.force_login(self.user_mgr)
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        track_out_url = reverse('workorder-step-track-out', kwargs={'pk': self.wo_step.pk})

        # Case A: readiness check passes (shortage check) -> raw material stock_quantity=10, work order needs 5x1=5, enough
        response = self.client.post(track_in_url, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'IN_PROGRESS')
        self.assertEqual(self.work_order.refresh_status_from_steps(), 'IN_PROGRESS')

        # Case B: material deduction on completion and finished-goods inbound (Track Out enforces quantities and balance)
        response = self.client.post(track_out_url, {
            'received_quantity': 5, 'good_quantity': 5, 'defect_quantity': 0, 'loss_quantity': 0,
            'action': 'trackout',
        }, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'COMPLETED')

        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.status, 'COMPLETED')

        # Verify raw material stock was deducted (10 - 5 = 5)
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_quantity, 5)

        # Verify finished-goods stock increased (5 + 5 = 10)
        self.product_material.refresh_from_db()
        self.assertEqual(self.product_material.stock_quantity, 10)

        # Verify INBOUND and OUTBOUND stock transactions exist
        self.assertTrue(StockTransaction.objects.filter(reference=self.work_order.order_number, type='OUTBOUND').exists())
        self.assertTrue(StockTransaction.objects.filter(reference=self.work_order.order_number, type='INBOUND').exists())

    def test_shortage_precheck_blocking(self):
        """Test 5: insufficient raw material on Track In must be blocked"""
        # Manually drop the screen material stock to 2 (the work order needs 5)
        self.material.stock_quantity = 2
        self.material.save()

        self.client.force_login(self.user_mgr)
        url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        response = self.client.post(url, follow=True)

        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'PENDING')  # stays PENDING due to the shortage

    def test_cancelled_step_does_not_block_completion(self):
        """Test 6: one step cancelled, the rest completed -> work order must be Completed (cancelled counts as skipped)"""
        s2 = WorkOrderStep.objects.create(
            work_order=self.work_order, step_number=2, name='Assembly', status='PENDING'
        )
        s3 = WorkOrderStep.objects.create(
            work_order=self.work_order, step_number=3, name='Inspection', status='PENDING'
        )
        # Steps 1 and 3 completed, step 2 cancelled
        self.wo_step.status = 'COMPLETED'
        self.wo_step.actual_end_date = timezone.now()
        self.wo_step.save()
        s2.status = 'CANCELLED'
        s2.save()
        s3.status = 'COMPLETED'
        s3.actual_end_date = timezone.now()
        s3.save()

        self.assertEqual(self.work_order.refresh_status_from_steps(), 'COMPLETED')

    def test_all_steps_cancelled_is_cancelled(self):
        """Test 7: all steps cancelled -> work order must be Cancelled"""
        s2 = WorkOrderStep.objects.create(
            work_order=self.work_order, step_number=2, name='Assembly', status='PENDING'
        )
        self.wo_step.status = 'CANCELLED'
        self.wo_step.save()
        s2.status = 'CANCELLED'
        s2.save()

        self.assertEqual(self.work_order.refresh_status_from_steps(), 'CANCELLED')

    def test_workorder_qrcode_returns_png(self):
        """Test 8: the work order QR-Code endpoint returns a PNG (encoding the work order number)"""
        self.client.force_login(self.user_mgr)
        url = reverse('workorder-qrcode', kwargs={'pk': self.work_order.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        # PNG magic number check
        self.assertEqual(response.content[:8], b'\x89PNG\r\n\x1a\n')

    def test_strict_serial_blocks_track_in_next_step(self):
        """Test 9: strict serial flow — the next step cannot Track In while the previous step has not tracked out"""
        s2 = WorkOrderStep.objects.create(
            work_order=self.work_order, step_number=2, name='Assembly', status='PENDING'
        )
        self.client.force_login(self.user_mgr)
        url = reverse('workorder-step-track-in', kwargs={'pk': s2.pk})

        # Previous step (step 1) has not tracked out yet -> blocked
        response = self.client.post(url, follow=True)
        s2.refresh_from_db()
        self.assertEqual(s2.status, 'PENDING')

        # Once the previous step is completed, track in is allowed
        self.wo_step.status = 'COMPLETED'
        self.wo_step.actual_end_date = timezone.now()
        self.wo_step.save()
        response = self.client.post(url, follow=True)
        s2.refresh_from_db()
        self.assertEqual(s2.status, 'IN_PROGRESS')

    def test_track_out_requires_balanced_quantity(self):
        """Test 10: Track Out enforces quantities — missing or unbalanced quantities block track out"""
        self.client.force_login(self.user_mgr)
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        track_out_url = reverse('workorder-step-track-out', kwargs={'pk': self.wo_step.pk})

        self.client.post(track_in_url, follow=True)

        # Quantities missing -> blocked
        response = self.client.post(track_out_url, {'action': 'trackout'}, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'IN_PROGRESS')

        # Unbalanced quantities (good 3 + defect 0 + loss 1 = 4 != received 5) -> blocked
        response = self.client.post(track_out_url, {
            'received_quantity': 5, 'good_quantity': 3, 'defect_quantity': 0, 'loss_quantity': 1,
            'action': 'trackout',
        }, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'IN_PROGRESS')

    def test_track_in_out_records_operator_equipment(self):
        """Test 11: Track In/Out records the operator, actual equipment and timestamps"""
        self.client.force_login(self.user_mgr)
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        track_out_url = reverse('workorder-step-track-out', kwargs={'pk': self.wo_step.pk})

        self.client.post(track_in_url, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.track_in_by, self.user_mgr)
        self.assertEqual(self.wo_step.actual_equipment, self.equipment)  # snapshots the planned equipment
        self.assertIsNotNone(self.wo_step.actual_start_date)

        self.client.post(track_out_url, {
            'received_quantity': 5, 'good_quantity': 5, 'defect_quantity': 0, 'loss_quantity': 0,
            'action': 'trackout',
        }, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.track_out_by, self.user_mgr)
        self.assertIsNotNone(self.wo_step.actual_end_date)

    def test_track_out_flows_quantities_to_next_step(self):
        """Test 12: after track out, good/defect/received quantities flow automatically to the next step"""
        s2 = WorkOrderStep.objects.create(
            work_order=self.work_order, step_number=2, name='Assembly', status='PENDING'
        )
        self.client.force_login(self.user_mgr)
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        track_out_url = reverse('workorder-step-track-out', kwargs={'pk': self.wo_step.pk})

        self.client.post(track_in_url, follow=True)
        # Track out: received 7 = good 5 + defect 1 + loss 1
        self.client.post(track_out_url, {
            'received_quantity': 7, 'good_quantity': 5, 'defect_quantity': 1, 'loss_quantity': 1,
            'action': 'trackout',
        }, follow=True)

        s2.refresh_from_db()
        self.assertEqual(s2.received_quantity, 6)   # flow = good 5 + defect 1 (loss does not flow)
        self.assertEqual(s2.good_quantity, 5)
        self.assertEqual(s2.defect_quantity, 1)

    def test_track_out_skips_cancelled_next_step(self):
        """Test 13: when the next step is cancelled, quantities flow to the step after it (skipping cancelled steps)"""
        s2 = WorkOrderStep.objects.create(
            work_order=self.work_order, step_number=2, name='Skipped Station', status='CANCELLED'
        )
        s3 = WorkOrderStep.objects.create(
            work_order=self.work_order, step_number=3, name='Inspection', status='PENDING'
        )
        self.client.force_login(self.user_mgr)
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        track_out_url = reverse('workorder-step-track-out', kwargs={'pk': self.wo_step.pk})

        self.client.post(track_in_url, follow=True)
        self.client.post(track_out_url, {
            'received_quantity': 5, 'good_quantity': 5, 'defect_quantity': 0, 'loss_quantity': 0,
            'action': 'trackout',
        }, follow=True)

        s3.refresh_from_db()
        self.assertEqual(s3.received_quantity, 5)
        self.assertEqual(s3.good_quantity, 5)
        # The cancelled s2 must not receive the flow
        self.assertIsNone(s2.received_quantity)

    def test_track_in_form_page_renders(self):
        """Test 14: the Track In form page (GET) renders correctly"""
        self.client.force_login(self.user_mgr)
        url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Track In')
        self.assertContains(response, 'Received Quantity')

    def test_track_in_records_quantity_and_note(self):
        """Test 15: Track In records the received quantity and the track-in note/condition"""
        self.client.force_login(self.user_mgr)
        url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        response = self.client.post(url, {
            'received_quantity': 8,
            'track_in_note': 'Appearance check found 2 scratched parts, awaiting confirmation',
        }, follow=True)
        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'IN_PROGRESS')
        self.assertEqual(self.wo_step.received_quantity, 8)
        self.assertEqual(self.wo_step.track_in_note, 'Appearance check found 2 scratched parts, awaiting confirmation')
        self.assertEqual(self.wo_step.track_in_by, self.user_mgr)

    def test_track_out_records_note(self):
        """Test 16: Track Out records the track-out note/condition"""
        self.client.force_login(self.user_mgr)
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': self.wo_step.pk})
        track_out_url = reverse('workorder-step-track-out', kwargs={'pk': self.wo_step.pk})

        self.client.post(track_in_url, {'received_quantity': 5}, follow=True)
        self.client.post(track_out_url, {
            'received_quantity': 5, 'good_quantity': 5, 'defect_quantity': 0, 'loss_quantity': 0,
            'track_out_note': 'Equipment ran abnormally, maintenance completed',
            'action': 'trackout',
        }, follow=True)

        self.wo_step.refresh_from_db()
        self.assertEqual(self.wo_step.status, 'COMPLETED')
        self.assertEqual(self.wo_step.track_out_note, 'Equipment ran abnormally, maintenance completed')
        self.assertEqual(self.wo_step.track_out_by, self.user_mgr)

    # ── Picking Station (First Station) ────────────────────────────────────

    def _create_wo_with_picking(self, order_number='WO-PICK-001'):
        """Create a work order with a picking station via the create view (product has a BOM + standard process)"""
        self.client.force_login(self.user_mgr)
        response = self.client.post(reverse('workorder-add'), {
            'order_number': order_number,
            'product': self.product.pk,
            'quantity': 5,
            'type': 'NORMAL',
            'source': 'ORDER',
            'planned_start_date': '2026-08-01 08:00',
            'planned_end_date': '2026-08-02 08:00',
        })
        self.assertEqual(response.status_code, 302)
        return WorkOrder.objects.get(order_number=order_number)

    def test_workorder_create_builds_picking_step(self):
        """Test 17: creating a work order (with BOM) → auto-creates the picking first step and the material confirmation list"""
        wo = self._create_wo_with_picking()
        picking = wo.steps.filter(is_picking_step=True).first()
        self.assertIsNotNone(picking)
        self.assertEqual(picking.step_number, 0)
        self.assertEqual(picking.status, 'PENDING')
        # Material confirmation list: BOM quantity 1.0 × work order quantity 5 = required 5
        items = wo.picking_items.all()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().material, self.material)
        self.assertEqual(items.first().required_quantity, Decimal('5.0000'))

    def test_picking_page_renders(self):
        """Test 18: the picking confirmation page (GET) renders correctly and lists the materials"""
        wo = self._create_wo_with_picking()
        self.client.force_login(self.user_mgr)
        response = self.client.get(reverse('workorder-picking', kwargs={'pk': wo.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Picking Confirmation')
        self.assertContains(response, self.material.material_id)

    def test_picking_gates_next_step_track_in(self):
        """Test 19: picking not confirmed → the next process step cannot track in; allowed after confirmation (strict serial flow)"""
        wo = self._create_wo_with_picking()
        proc_step = wo.steps.exclude(is_picking_step=True).first()
        self.assertIsNotNone(proc_step)
        self.client.force_login(self.user_mgr)
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': proc_step.pk})

        # Picking not confirmed -> track in blocked
        response = self.client.post(track_in_url, {'received_quantity': 5}, follow=True)
        proc_step.refresh_from_db()
        self.assertEqual(proc_step.status, 'PENDING')

        # Confirm picking (enter the required quantity for each item)
        picking_url = reverse('workorder-picking', kwargs={'pk': wo.pk})
        data = {f'qty_{it.pk}': str(it.required_quantity) for it in wo.picking_items.all()}
        response = self.client.post(picking_url, data, follow=True)

        # Once the picking station is completed, the next step can track in
        response = self.client.post(track_in_url, {'received_quantity': 5}, follow=True)
        proc_step.refresh_from_db()
        self.assertEqual(proc_step.status, 'IN_PROGRESS')

    def test_picking_confirm_records_items_and_step(self):
        """Test 20: picking confirmation records each material's confirmed data and completes the picking station"""
        wo = self._create_wo_with_picking()
        picking = wo.steps.filter(is_picking_step=True).first()
        self.client.force_login(self.user_mgr)

        items = wo.picking_items.all()
        data = {}
        for it in items:
            data[f'qty_{it.pk}'] = '4'
            data[f'note_{it.pk}'] = 'Short by 1, to be replenished'
        response = self.client.post(reverse('workorder-picking', kwargs={'pk': wo.pk}), data, follow=True)

        picking.refresh_from_db()
        self.assertEqual(picking.status, 'COMPLETED')
        self.assertEqual(picking.track_in_by, self.user_mgr)
        self.assertEqual(picking.track_out_by, self.user_mgr)
        for it in items:
            it.refresh_from_db()
            self.assertEqual(it.confirmed_quantity, Decimal('4'))
            self.assertEqual(it.confirmed_by, self.user_mgr)
            self.assertIsNotNone(it.confirmed_at)
            self.assertEqual(it.note, 'Short by 1, to be replenished')

    def test_picking_confirm_deducts_stock(self):
        """Test 21: once picking is confirmed, stock is deducted directly and an OUTBOUND transaction is written"""
        wo = self._create_wo_with_picking()
        self.client.force_login(self.user_mgr)
        items = wo.picking_items.all()
        data = {f'qty_{it.pk}': '5' for it in items}
        response = self.client.post(reverse('workorder-picking', kwargs={'pk': wo.pk}), data, follow=True)

        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_quantity, 5)  # 10 - 5 = 5
        txn = StockTransaction.objects.filter(reference=wo.order_number, type='OUTBOUND').first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.quantity, Decimal('5'))
        self.assertEqual(txn.balance_after, Decimal('5'))

    def test_picking_blocked_when_confirm_exceeds_stock(self):
        """Test 22: confirmed quantity exceeding current stock → picking confirmation blocked and no stock deducted"""
        wo = self._create_wo_with_picking()
        self.material.stock_quantity = 2
        self.material.save()
        self.client.force_login(self.user_mgr)
        items = wo.picking_items.all()
        data = {f'qty_{it.pk}': '5' for it in items}
        response = self.client.post(reverse('workorder-picking', kwargs={'pk': wo.pk}), data, follow=True)

        picking = wo.steps.filter(is_picking_step=True).first()
        picking.refresh_from_db()
        self.assertEqual(picking.status, 'PENDING')  # not completed
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_quantity, 2)  # not deducted
        self.assertFalse(StockTransaction.objects.filter(reference=wo.order_number, type='OUTBOUND').exists())

    def test_picking_no_double_deduction_on_completion(self):
        """Test 23: picking already deducted stock → completing the work order must not deduct again (finished goods still auto-inbound)"""
        wo = self._create_wo_with_picking()
        self.client.force_login(self.user_mgr)

        # Confirm picking and deduct stock (10 - 5 = 5)
        items = wo.picking_items.all()
        data = {f'qty_{it.pk}': '5' for it in items}
        self.client.post(reverse('workorder-picking', kwargs={'pk': wo.pk}), data, follow=True)

        # Run the full process: Track In → Track Out (balanced quantities) → work order completed
        proc_step = wo.steps.exclude(is_picking_step=True).first()
        track_in_url = reverse('workorder-step-track-in', kwargs={'pk': proc_step.pk})
        track_out_url = reverse('workorder-step-track-out', kwargs={'pk': proc_step.pk})
        self.client.post(track_in_url, {'received_quantity': 5}, follow=True)
        self.client.post(track_out_url, {
            'received_quantity': 5, 'good_quantity': 5, 'defect_quantity': 0, 'loss_quantity': 0,
            'action': 'trackout',
        }, follow=True)

        wo.refresh_from_db()
        self.assertEqual(wo.status, 'COMPLETED')
        # Picking already deducted 5; completion must not deduct again (stays 5)
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_quantity, 5)
        # Finished goods auto-inbound
        self.product_material.refresh_from_db()
        self.assertEqual(self.product_material.stock_quantity, 10)
        # Only one OUTBOUND transaction, the one from picking confirmation
        self.assertEqual(
            StockTransaction.objects.filter(reference=wo.order_number, type='OUTBOUND').count(), 1
        )
