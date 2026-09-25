from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from Orgnization.models import Department, Position, Employee

User = get_user_model()


class DashboardTemplateTestCase(TestCase):
    """Dashboard template switch test: classic and industrial can switch between each other, saved in session"""

    def setUp(self):
        self.user = User.objects.create_user(username='dash_user', password='password123')
        dept = Department.objects.create(code='D001', name='Management')
        pos = Position.objects.create(code='P001', name='Manager')
        Employee.objects.create(
            user=self.user, emp_no='EMP-001', name='Tester',
            department=dept, position=pos, role='admin',
        )
        self.client.force_login(self.user)

    def test_default_is_classic(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_switch_to_industrial_persists_in_session(self):
        # ?template=industrial switch and persist in session
        response = self.client.get(reverse('dashboard'), {'template': 'industrial'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Industrial Dashboard')

        # Visit without param -> still industrial
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Industrial Dashboard')

    def test_switch_back_to_classic(self):
        self.client.get(reverse('dashboard'), {'template': 'industrial'})
        self.client.get(reverse('dashboard'), {'template': 'classic'})
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Dashboard')

    def test_invalid_template_ignored(self):
        response = self.client.get(reverse('dashboard'), {'template': 'hacker'})
        self.assertContains(response, 'Dashboard')

    def test_post_switch_endpoint(self):
        response = self.client.post(reverse('dashboard-template-switch'), {'template': 'industrial'})
        self.assertRedirects(response, reverse('dashboard'))
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Industrial Dashboard')
