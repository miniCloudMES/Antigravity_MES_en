from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from Orgnization.models import Employee
from Orgnization.tests_base import RoleAccessTestCase
from .models import MaterialCategory, Material


class MaterialPermissionTestCase(RoleAccessTestCase):
    """Material module: list requires login; add is restricted to admin/manager.

    Note: Material has migration seed data (MAT-001~005, MAT-T9, etc.),
    so assertions must check relative changes rather than assuming an empty table.
    """

    def setUp(self):
        super().setUp()
        self.category = MaterialCategory.objects.create(name='Raw Material')

    def test_list_requires_login(self):
        response = self.client.get(reverse('material-list'))
        self.assertEqual(response.status_code, 302)

    def test_operator_cannot_create_material(self):
        before = Material.objects.count()
        self._login(self.user_op)
        response = self.client.post(reverse('material-add'), {
            'material_id': 'MAT-N01',
            'name': 'Test Material',
            'category': self.category.pk,
            'unit': 'pcs',
            'min_stock': '10.00',
            'stock_quantity': '100.00',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Material.objects.count(), before)
        self.assertFalse(Material.objects.filter(material_id='MAT-N01').exists())

    def test_manager_can_create_material(self):
        self._login(self.user_mgr)
        response = self.client.post(reverse('material-add'), {
            'material_id': 'MAT-N01',
            'name': 'Test Material',
            'category': self.category.pk,
            'unit': 'pcs',
            'min_stock': '10.00',
        })
        self.assertEqual(response.status_code, 302)
        created = Material.objects.get(material_id='MAT-N01')
        # Newly created material stock is always 0; inbound requires stock transactions
        self.assertEqual(created.stock_quantity, 0)

    def test_create_material_ignores_posted_stock_quantity(self):
        """Stock field is removed from form; even if POST includes stock_quantity it is ignored."""
        self._login(self.user_mgr)
        response = self.client.post(reverse('material-add'), {
            'material_id': 'MAT-N02',
            'name': 'Test Material 2',
            'category': self.category.pk,
            'unit': 'pcs',
            'min_stock': '10.00',
            'stock_quantity': '9999.00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Material.objects.get(material_id='MAT-N02').stock_quantity, 0)

    def test_edit_material_does_not_change_stock_quantity(self):
        """Editing material must not alter stock quantity."""
        mat = Material.objects.create(
            material_id='MAT-N03', name='Test Material 3',
            category=self.category, unit='pcs', stock_quantity=50,
        )
        self._login(self.user_mgr)
        response = self.client.post(reverse('material-edit', kwargs={'pk': mat.pk}), {
            'material_id': 'MAT-N03',
            'name': 'Test Material 3 (Renamed)',
            'category': self.category.pk,
            'unit': 'pcs',
            'min_stock': '10.00',
            'stock_quantity': '1.00',
        })
        self.assertEqual(response.status_code, 302)
        mat.refresh_from_db()
        self.assertEqual(mat.name, 'Test Material 3 (Renamed)')
        self.assertEqual(mat.stock_quantity, 50)

    def test_edit_material_form_has_no_stock_input(self):
        """Edit page only displays read-only stock and provides no editable stock field."""
        mat = Material.objects.create(
            material_id='MAT-N04', name='Test Material 4',
            category=self.category, unit='pcs', stock_quantity=30,
        )
        self._login(self.user_mgr)
        response = self.client.get(reverse('material-edit', kwargs={'pk': mat.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock Quantity')
        self.assertNotContains(response, 'name="stock_quantity"')


class MaterialTransactionListFilterTests(TestCase):
    """Material stock transaction list: date range filter, single item view, and summaries."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from .models import StockTransaction

        self.StockTransaction = StockTransaction
        self.category = MaterialCategory.objects.create(name='Filter Test Category')
        self.mat_a = Material.objects.create(
            material_id='MAT-FLT-A', name='MaterialA', category=self.category,
            unit='pcs', stock_quantity=0,
        )
        self.mat_b = Material.objects.create(
            material_id='MAT-FLT-B', name='MaterialB', category=self.category,
            unit='pcs', stock_quantity=0,
        )
        User = get_user_model()
        self.admin = User.objects.create_superuser('admin_matflt', 'm@m.com', 'pw123456')
        Employee.objects.create(emp_no='EMP-M01', name='MaterialFilter Admin', role='admin', user=self.admin)
        self.client = Client()
        self.client.force_login(self.admin)

        StockTransaction.objects.create(
            material=self.mat_a, type='INBOUND', quantity=Decimal('10'),
            balance_after=Decimal('10'),
        )
        StockTransaction.objects.create(
            material=self.mat_b, type='OUTBOUND', quantity=Decimal('4'),
            balance_after=Decimal('-4'),
        )

    def _list_url(self):
        return reverse('stock-transaction-list')

    def test_list_renders_without_filters(self):
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['summary_count'], 2)

    def test_filter_by_exact_material_pk(self):
        """Clicking ?material=<pk> from material list only shows that material."""
        resp = self.client.get(self._list_url(), {'material': self.mat_a.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['summary_count'], 1)
        self.assertEqual(resp.context['filtered_material'].pk, self.mat_a.pk)
        self.assertContains(resp, 'MAT-FLT-A')
        self.assertNotContains(resp, 'MAT-FLT-B')

    def test_filter_by_material_id_substring(self):
        resp = self.client.get(self._list_url(), {'material_id': 'MAT-FLT-B'})
        self.assertEqual(resp.context['summary_count'], 1)

    def test_filter_by_date_range_excludes_all(self):
        """Out of date range (future) should not show any records."""
        from datetime import date, timedelta
        future = (date.today() + timedelta(days=1)).isoformat()
        resp = self.client.get(self._list_url(), {'date_from': future})
        self.assertEqual(resp.context['summary_count'], 0)

    def test_type_totals_split_correctly(self):
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.context['summary_inbound'], Decimal('10'))
        self.assertEqual(resp.context['summary_outbound'], Decimal('4'))

    def test_summary_zero_when_no_rows(self):
        resp = self.client.get(self._list_url(), {'material_id': 'NO-SUCH-MATERIAL'})
        self.assertEqual(resp.context['summary_count'], 0)
        self.assertEqual(resp.context['summary_inbound'], 0)

    def test_material_list_links_to_transaction_history(self):
        """Each row in Material list should have a clickable transaction history link."""
        resp = self.client.get(reverse('material-list'))
        self.assertEqual(resp.status_code, 200)
        expected = f"{reverse('stock-transaction-list')}?material={self.mat_a.pk}"
        self.assertContains(resp, expected)

