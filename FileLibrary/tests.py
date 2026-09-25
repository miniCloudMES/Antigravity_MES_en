from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from Orgnization.tests_base import RoleAccessTestCase
from .models import LibraryFile


class FileLibraryPermissionTestCase(RoleAccessTestCase):
    """File library: list requires login; upload is restricted to admin/manager (operator denied)."""

    def _make_file(self):
        return SimpleUploadedFile(
            'test.txt',
            BytesIO(b'hello mes').read(),
            content_type='text/plain',
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse('filelibrary:file-library-list'))
        self.assertEqual(response.status_code, 302)

    def test_operator_cannot_upload(self):
        self._login(self.user_op)
        response = self.client.post(reverse('filelibrary:file-upload'), {
            'title': 'Test File',
            'file': self._make_file(),
        })
        self.assertEqual(response.status_code, 302)  # Redirected to list with permission error message
        self.assertEqual(LibraryFile.objects.count(), 0)

    def test_manager_can_upload(self):
        self._login(self.user_mgr)
        response = self.client.post(reverse('filelibrary:file-upload'), {
            'title': 'Test File',
            'file': self._make_file(),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LibraryFile.objects.count(), 1)
        self.assertEqual(LibraryFile.objects.get().uploaded_by, self.user_mgr)
