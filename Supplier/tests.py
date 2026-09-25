from django.urls import reverse

from Orgnization.tests_base import RoleAccessTestCase
from .models import SupplierCategory, Supplier


class SupplierPermissionTestCase(RoleAccessTestCase):
    """Supplier module: list requires login; add is restricted to admin/manager."""

    def setUp(self):
        super().setUp()
        self.category = SupplierCategory.objects.create(name='Raw Material Supplier')

    def test_list_requires_login(self):
        response = self.client.get(reverse('supplier-list'))
        self.assertEqual(response.status_code, 302)  # Not logged in -> redirect to login page

    def test_operator_cannot_create_supplier(self):
        self._login(self.user_op)
        response = self.client.post(reverse('supplier-add'), {
            'supplier_id': 'SUP-001',
            'name': 'Test Supplier',
            'category': self.category.pk,
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Supplier.objects.count(), 0)

    def test_manager_can_create_supplier(self):
        self._login(self.user_mgr)
        response = self.client.post(reverse('supplier-add'), {
            'supplier_id': 'SUP-001',
            'name': 'Test Supplier',
            'category': self.category.pk,
        })
        self.assertEqual(response.status_code, 302)  # Success -> redirect to Supplier list
        self.assertEqual(Supplier.objects.count(), 1)

    def test_supplier_id_must_be_unique(self):
        Supplier.objects.create(supplier_id='SUP-001', name='Existing Supplier', category=self.category)
        self._login(self.user_mgr)
        response = self.client.post(reverse('supplier-add'), {
            'supplier_id': 'SUP-001',
            'name': 'Duplicate Supplier',
            'category': self.category.pk,
        })
        self.assertEqual(response.status_code, 200)  # Form validation failed, stay on form page
        self.assertEqual(Supplier.objects.count(), 1)
