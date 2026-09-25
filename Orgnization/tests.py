from django.urls import reverse

from Orgnization.tests_base import RoleAccessTestCase
from .models import Employee, Department, Position
from django.contrib.auth import get_user_model

User = get_user_model()


class OrgnizationPermissionTestCase(RoleAccessTestCase):
    """Organization module: employee list requires login; add is restricted to admin/manager."""

    def test_employee_list_requires_login(self):
        response = self.client.get(reverse('employee-list'))
        self.assertEqual(response.status_code, 302)

    def test_operator_cannot_create_employee(self):
        self._login(self.user_op)
        response = self.client.post(reverse('employee-add'), {
            'emp_no': 'EMP-100',
            'name': 'New Employee',
            'role': 'operator',
            'department': self.dept.pk,
            'position': self.pos.pk,
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Employee.objects.count(), 3)  # Originally 3 test employees

    def test_manager_can_create_employee_with_account(self):
        self._login(self.user_mgr)
        user_count_before = User.objects.count()
        response = self.client.post(reverse('employee-add'), {
            'emp_no': 'EMP-100',
            'name': 'New Employee',
            'gender': 'M',
            'role': 'operator',
            'department': self.dept.pk,
            'position': self.pos.pk,
            'create_account': 'on',
        })
        # Account creation success -> render account credential page
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Employee.objects.count(), 4)
        self.assertEqual(User.objects.count(), user_count_before + 1)

    def test_employee_list_renders_department_position(self):
        """List should render department/position names (select_related)."""
        self._login(self.user_admin)
        response = self.client.get(reverse('employee-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Management')
        self.assertContains(response, 'Manager')


class SidebarNavTestCase(RoleAccessTestCase):
    """Sidebar navigation: Stock transaction links should be directly clickable."""

    def test_sidebar_has_stock_transaction_links(self):
        self._login(self.user_mgr)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inventory')
        self.assertContains(response, reverse('stock-transaction-list'))
        self.assertContains(response, reverse('product-stock-transaction-list'))

    def test_transaction_pages_reachable_from_sidebar_urls(self):
        """Both transaction URLs in the sidebar should open normally."""
        self._login(self.user_mgr)
        for url_name in ('stock-transaction-list', 'product-stock-transaction-list'):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
