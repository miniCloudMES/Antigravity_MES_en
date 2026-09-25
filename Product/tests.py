from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from Orgnization.models import Employee
from .models import Product, ProductCategory, ProductStockTransaction


class ProductStorageControlTests(TestCase):
    def setUp(self):
        self.cat = ProductCategory.objects.create(name='Test Category')
        self.prod = Product.objects.create(
            product_id='PRD-TEST-001',
            name='Test Product',
            category=self.cat,
            unit='pcs',
            stock_quantity=Decimal('10'),
            min_stock=Decimal('3'),
        )
        self.admin = User.objects.create_superuser('admin_test', 'a@a.com', 'pw123456')
        Employee.objects.create(emp_no='EMP-001', name='Test Admin', role='admin', user=self.admin)
        self.client = Client()
        self.client.force_login(self.admin)

    def test_is_low_stock_property(self):
        self.assertFalse(self.prod.is_low_stock)
        self.prod.stock_quantity = Decimal('2')
        self.assertTrue(self.prod.is_low_stock)

    def test_quick_inbound_updates_stock_and_creates_txn(self):
        url = reverse('product-quick-transaction', kwargs={'product_pk': self.prod.pk})
        resp = self.client.post(url, {'type': 'INBOUND', 'quantity': '5', 'reference': '', 'remark': ''})
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_quantity, Decimal('15'))
        txn = ProductStockTransaction.objects.get(product=self.prod)
        self.assertEqual(txn.type, 'INBOUND')
        self.assertEqual(txn.balance_after, Decimal('15'))

    def test_outbound_more_than_stock_blocked(self):
        url = reverse('product-quick-transaction', kwargs={'product_pk': self.prod.pk})
        resp = self.client.post(url, {'type': 'OUTBOUND', 'quantity': '99', 'reference': '', 'remark': ''})
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_quantity, Decimal('10'))
        self.assertFalse(ProductStockTransaction.objects.exists())

    def test_transaction_list_page_renders(self):
        ProductStockTransaction.objects.create(
            product=self.prod, type='INBOUND', quantity='5',
            balance_after='15', reference='WO-1', created_by=self.admin,
        )
        resp = self.client.get(reverse('product-stock-transaction-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'PRD-TEST-001')

    def test_add_transaction_page_renders(self):
        resp = self.client.get(reverse('product-stock-transaction-add'))
        self.assertEqual(resp.status_code, 200)

    def test_quick_form_page_renders(self):
        url = reverse('product-quick-transaction', kwargs={'product_pk': self.prod.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_product_list_shows_stock_column(self):
        resp = self.client.get(reverse('product-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Stock')
        self.assertContains(resp, 'data-p-stock')

    def test_product_form_shows_readonly_stock(self):
        """The product form only shows read-only stock and must not offer an editable stock_quantity field."""
        resp = self.client.get(reverse('product-edit', kwargs={'pk': self.prod.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Stock Quantity')
        self.assertNotContains(resp, 'name="stock_quantity"')

    def test_edit_product_does_not_change_stock_quantity(self):
        """Editing a product must not change the stock quantity."""
        resp = self.client.post(reverse('product-edit', kwargs={'pk': self.prod.pk}), {
            'product_id': self.prod.product_id,
            'name': 'Test Product (renamed)',
            'category': self.prod.category.pk,
            'unit': 'pcs',
            'min_stock': '5.00',
            'is_active': 'on',
            'stock_quantity': '999.00',
        })
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.name, 'Test Product (renamed)')
        self.assertEqual(self.prod.stock_quantity, Decimal('10'))

    def test_dashboard_low_stock_context(self):
        self.prod.min_stock = Decimal('20')  # make it low
        self.prod.save()
        resp = self.client.get(reverse('product-dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['low_stock_count'], 1)


class ProductTransactionListFilterTests(TestCase):
    """Product stock transaction list: date range filtering, single-item view and totals."""

    def setUp(self):
        self.cat = ProductCategory.objects.create(name='Filter Test Category')
        self.prod_a = Product.objects.create(
            product_id='PRD-FLT-A', name='Product A', category=self.cat,
            unit='pcs', stock_quantity=Decimal('0'),
        )
        self.prod_b = Product.objects.create(
            product_id='PRD-FLT-B', name='Product B', category=self.cat,
            unit='pcs', stock_quantity=Decimal('0'),
        )
        self.admin = User.objects.create_superuser('admin_flt', 'f@f.com', 'pw123456')
        Employee.objects.create(emp_no='EMP-F01', name='Filter Admin', role='admin', user=self.admin)
        self.client = Client()
        self.client.force_login(self.admin)

        self.txn_a = ProductStockTransaction.objects.create(
            product=self.prod_a, type='INBOUND', quantity=Decimal('10'),
            balance_after=Decimal('10'),
        )
        self.txn_b = ProductStockTransaction.objects.create(
            product=self.prod_b, type='INBOUND', quantity=Decimal('20'),
            balance_after=Decimal('20'),
        )

    def _list_url(self):
        return reverse('product-stock-transaction-list')

    def test_list_renders_without_filters(self):
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['summary_count'], 2)
        self.assertEqual(resp.context['summary_inbound'], Decimal('30'))

    def test_filter_by_exact_product_pk(self):
        """?product=<pk> from product list only shows that product."""
        resp = self.client.get(self._list_url(), {'product': self.prod_a.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['summary_count'], 1)
        self.assertEqual(resp.context['filtered_product'].pk, self.prod_a.pk)
        self.assertContains(resp, 'PRD-FLT-A')
        self.assertNotContains(resp, 'PRD-FLT-B')

    def test_filter_by_product_id_substring(self):
        resp = self.client.get(self._list_url(), {'product_id': 'PRD-FLT-B'})
        self.assertEqual(resp.context['summary_count'], 1)
        self.assertContains(resp, 'PRD-FLT-B')
        self.assertNotContains(resp, 'PRD-FLT-A')

    def test_filter_by_date_range_excludes_older(self):
        """Records outside date range (future dates in this case) must not appear."""
        from datetime import date, timedelta
        future = (date.today() + timedelta(days=1)).isoformat()
        resp = self.client.get(self._list_url(), {'date_from': future})
        self.assertEqual(resp.context['summary_count'], 0)

    def test_date_range_and_type_totals_are_independent_of_pagination(self):
        """Totals should be based on filtered results, unaffected by pagination."""
        resp = self.client.get(self._list_url(), {'type': 'INBOUND'})
        self.assertEqual(resp.context['summary_inbound'], Decimal('30'))
        self.assertEqual(resp.context['summary_outbound'], Decimal('0'))
        self.assertEqual(resp.context['summary_adjust'], Decimal('0'))

    def test_base_query_excludes_page_param(self):
        """Pagination query string must not carry 'page' param or it stacks infinitely."""
        resp = self.client.get(self._list_url(), {'type': 'INBOUND'})
        self.assertNotIn('page', resp.context['base_query'])
        self.assertEqual(resp.context['base_query'], 'type=INBOUND')

    def test_summary_shows_zero_not_blank_when_no_rows(self):
        """Totals should be 0 when there is no data, not blank."""
        resp = self.client.get(self._list_url(), {'product_id': 'NO-SUCH-PRODUCT'})
        self.assertEqual(resp.context['summary_count'], 0)
        self.assertEqual(resp.context['summary_inbound'], 0)

