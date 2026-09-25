"""
Shared role permission test base.

Creates admin / manager / operator employees and provides login helpers,
allowing tests.py in other modules to inherit directly and avoid repetitive boilerplate.
(Filename does not start with test_, so it is not treated as a test module by Django test discovery.)
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import Department, Position, Employee

User = get_user_model()


class RoleAccessTestCase(TestCase):
    """Test base providing three distinct role employees and login helpers."""

    def setUp(self):
        self.dept = Department.objects.create(code='D001', name='Management')
        self.pos = Position.objects.create(code='P001', name='Manager')

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
