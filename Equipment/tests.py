from django.urls import reverse

from Orgnization.tests_base import RoleAccessTestCase
from .models import EquipmentCategory, Equipment


class EquipmentPermissionTestCase(RoleAccessTestCase):
    """Equipment module: the list requires login, creating requires admin/manager."""

    def setUp(self):
        super().setUp()
        self.category = EquipmentCategory.objects.create(name='Production Equipment')

    def test_list_requires_login(self):
        response = self.client.get(reverse('equipment-list'))
        self.assertEqual(response.status_code, 302)

    def test_operator_cannot_create_equipment(self):
        self._login(self.user_op)
        response = self.client.post(reverse('equipment-add'), {
            'equipment_id': 'EQ-001',
            'name': 'Test Equipment',
            'category': self.category.pk,
            'status': 'active',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Equipment.objects.count(), 0)

    def test_manager_can_create_equipment(self):
        self._login(self.user_mgr)
        response = self.client.post(reverse('equipment-add'), {
            'equipment_id': 'EQ-001',
            'name': 'Test Equipment',
            'category': self.category.pk,
            'status': 'active',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Equipment.objects.count(), 1)

    def test_list_renders_with_select_related(self):
        """The list page should render correctly without N+1 errors."""
        Equipment.objects.create(equipment_id='EQ-001', name='Test Equipment', category=self.category)
        self._login(self.user_op)
        response = self.client.get(reverse('equipment-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Equipment')
