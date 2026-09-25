from django.urls import reverse

from Orgnization.tests_base import RoleAccessTestCase
from .models import DocumentCategory, Document


class DocumentCreateTestCase(RoleAccessTestCase):
    """Documents module: creating a draft only requires login (submission and review have separate permission checks)."""

    def setUp(self):
        super().setUp()
        self.category = DocumentCategory.objects.create(name='Work Instructions')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('documents-dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_operator_can_create_draft_document(self):
        self._login(self.user_op)
        response = self.client.post(reverse('document-create'), {
            'code': 'DOC-001',
            'title': 'Test Document',
            'category': self.category.pk,
            'department': self.dept.pk,
            'content': 'Document Content',
        })
        self.assertEqual(response.status_code, 302)  # success → redirect to the document detail
        self.assertEqual(Document.objects.count(), 1)
        document = Document.objects.get()
        self.assertEqual(document.status, Document.STATUS_DRAFT)
        self.assertEqual(document.created_by, self.user_op)
