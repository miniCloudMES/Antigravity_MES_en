import tempfile
from io import BytesIO
from urllib.parse import unquote

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='mes-test-media-'))
class FileDownloadHeaderTestCase(RoleAccessTestCase):
    """Download headers must stay ASCII.

    Regression: a non-ASCII filename made Django RFC 2047-encode the
    X-Accel-Redirect header (``=?utf-8?b?...?=``); nginx cannot decode that, so
    it resolved a bogus relative path and every Chinese-named file 404'd.
    """

    def _make_file(self, name):
        return LibraryFile.objects.create(
            title='CJK named file',
            file=SimpleUploadedFile(name, BytesIO(b'%PDF-1.4 test').read(), content_type='application/pdf'),
        )

    def test_non_ascii_filename_download_headers_are_ascii(self):
        obj = self._make_file('康軒英語.pdf')
        self._login(self.user_admin)

        response = self.client.get(reverse('filelibrary:file-download', args=[obj.pk]))
        self.assertEqual(response.status_code, 200)

        accel = response['X-Accel-Redirect']
        self.assertTrue(accel.startswith('/internal_media/'))
        accel.encode('ascii')                     # raises UnicodeEncodeError if not ASCII
        self.assertNotIn('=?utf-8?', accel)       # must not be an RFC 2047 encoded-word
        self.assertIn('康軒英語.pdf', unquote(accel))  # nginx can map it back to the real path

        disposition = response['Content-Disposition']
        disposition.encode('ascii')
        self.assertNotIn('=?utf-8?', disposition)
        self.assertIn("filename*=UTF-8''", disposition)
        # ASCII fallback must be usable, not a degenerate '.pdf'
        self.assertIn('filename="download.pdf"', disposition)

    def test_ascii_filename_unchanged(self):
        obj = self._make_file('plain.pdf')
        self._login(self.user_admin)

        response = self.client.get(reverse('filelibrary:file-download', args=[obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Accel-Redirect'], '/internal_media/file_library/plain.pdf')
        self.assertIn('filename="plain.pdf"', response['Content-Disposition'])
