from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from Orgnization.models import Department, Position, Employee
from .models import Customer

User = get_user_model()


class CustomerPermissionTestCase(TestCase):
    """Customer module role permission tests: Add/Edit/Delete restricted to admin and manager; operator can only view"""

    def setUp(self):
        self.dept = Department.objects.create(code='D001', name='Sales Department')
        self.pos = Position.objects.create(code='P001', name='Sales Representative')

        self.user_admin = User.objects.create_user(username='admin_user', password='password123')
        self.emp_admin = Employee.objects.create(
            user=self.user_admin, emp_no='EMP-001', name='Admin',
            department=self.dept, position=self.pos, role='admin',
        )

        self.user_mgr = User.objects.create_user(username='mgr_user', password='password123')
        self.emp_mgr = Employee.objects.create(
            user=self.user_mgr, emp_no='EMP-002', name='Manager',
            department=self.dept, position=self.pos, role='manager',
        )

        self.user_op = User.objects.create_user(username='op_user', password='password123')
        self.emp_op = Employee.objects.create(
            user=self.user_op, emp_no='EMP-003', name='Operator',
            department=self.dept, position=self.pos, role='operator',
        )

    def _login(self, user):
        # force_login directly logs in with auth.User (bypassing EmployeeNoBackend emp_no lookup)
        self.client.force_login(user)

    def test_operator_cannot_create_customer(self):
        self._login(self.user_op)
        response = self.client.post(reverse('customer:customer-add'), {
            'customer_id': 'CUST-001', 'name': 'Test Customer',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Customer.objects.count(), 0)

    def test_manager_can_create_customer(self):
        self._login(self.user_mgr)
        response = self.client.post(reverse('customer:customer-add'), {
            'customer_id': 'CUST-001', 'name': 'Test Customer',
        })
        self.assertEqual(response.status_code, 302)  # Success -> redirect to Customer list
        self.assertEqual(Customer.objects.count(), 1)

    def test_operator_cannot_edit_customer(self):
        customer = Customer.objects.create(customer_id='CUST-001', name='Old Name')
        self._login(self.user_op)
        response = self.client.post(reverse('customer:customer-edit', kwargs={'pk': customer.pk}), {
            'customer_id': 'CUST-001', 'name': 'New Name',
        })
        self.assertEqual(response.status_code, 403)
        customer.refresh_from_db()
        self.assertEqual(customer.name, 'Old Name')

    def test_manager_can_edit_customer(self):
        customer = Customer.objects.create(customer_id='CUST-001', name='Old Name')
        self._login(self.user_mgr)
        response = self.client.post(reverse('customer:customer-edit', kwargs={'pk': customer.pk}), {
            'customer_id': 'CUST-001', 'name': 'New Name',
        })
        self.assertEqual(response.status_code, 302)
        customer.refresh_from_db()
        self.assertEqual(customer.name, 'New Name')

    def test_operator_cannot_delete_customer(self):
        customer = Customer.objects.create(customer_id='CUST-001', name='Test Customer')
        self._login(self.user_op)
        response = self.client.post(reverse('customer:customer-delete', kwargs={'pk': customer.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())

    def test_admin_can_delete_customer(self):
        customer = Customer.objects.create(customer_id='CUST-001', name='Test Customer')
        self._login(self.user_admin)
        response = self.client.post(reverse('customer:customer-delete', kwargs={'pk': customer.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Customer.objects.filter(pk=customer.pk).exists())

    def test_operator_can_view_customer_list_and_detail(self):
        customer = Customer.objects.create(customer_id='CUST-001', name='Test Customer')
        self._login(self.user_op)
        list_resp = self.client.get(reverse('customer:customer-list'))
        self.assertEqual(list_resp.status_code, 200)
        detail_resp = self.client.get(reverse('customer:customer-detail', kwargs={'pk': customer.pk}))
        self.assertEqual(detail_resp.status_code, 200)
