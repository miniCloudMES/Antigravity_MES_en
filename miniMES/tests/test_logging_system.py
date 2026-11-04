"""Tests for the file-based logging system.

They assert on the log files themselves, which is the only honest way to prove
that login/logout, data changes and system errors are really written.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from Orgnization.models import Employee

LOG_DIR = Path(settings.LOG_DIR)
AUDIT_LOG = LOG_DIR / 'miniMES_audit.log'
ERROR_LOG = LOG_DIR / 'miniMES_error.log'
INFO_LOG = LOG_DIR / 'miniMES_info.log'

PASSWORD = 'Str0ng-Pass!234'


def _size(path):
    return path.stat().st_size if path.exists() else 0


def _read_since(path, offset):
    if not path.exists():
        return ''
    with path.open(encoding='utf-8') as handle:
        handle.seek(offset)
        return handle.read()


class LogFileMixin:
    """Reads only what the current test appended to each log file."""

    LOGS = (AUDIT_LOG, ERROR_LOG, INFO_LOG)

    def reset_offsets(self):
        self._offsets = {path: _size(path) for path in self.LOGS}

    def setUp(self):
        super().setUp()
        self.reset_offsets()

    def audit_lines(self):
        return _read_since(AUDIT_LOG, self._offsets[AUDIT_LOG])

    def error_lines(self):
        return _read_since(ERROR_LOG, self._offsets[ERROR_LOG])


class AuthLoggingTests(LogFileMixin, TestCase):
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username='karo', password=PASSWORD)
        Employee.objects.create(emp_no='E1001', name='Karo Lin', user=user)
        self.reset_offsets()  # fixture writes are not interesting

    def test_successful_login_is_logged(self):
        response = self.client.post(
            '/accounts/login/', {'username': 'E1001', 'password': PASSWORD}
        )
        self.assertEqual(response.status_code, 302)

        lines = self.audit_lines()
        self.assertIn('AUTH LOGIN', lines)
        self.assertIn('user=karo(E1001)', lines)
        self.assertIn('ip=127.0.0.1', lines)
        self.assertIn('path=/accounts/login/', lines)

    def test_logout_is_logged(self):
        self.client.post('/accounts/login/', {'username': 'E1001', 'password': PASSWORD})
        self.reset_offsets()

        self.client.post('/accounts/logout/')

        lines = self.audit_lines()
        self.assertIn('AUTH LOGOUT', lines)
        self.assertIn('user=karo(E1001)', lines)

    def test_failed_login_is_logged_without_the_password(self):
        self.client.post('/accounts/login/', {'username': 'E1001', 'password': 'not-the-password'})

        lines = self.audit_lines()
        self.assertIn('AUTH LOGIN_FAILED', lines)
        self.assertIn('username=E1001', lines)
        self.assertNotIn('not-the-password', lines)


@override_settings(ROOT_URLCONF='miniMES.tests.urls_for_logging')
class DataChangeLoggingTests(LogFileMixin, TestCase):
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username='auditor', password=PASSWORD)
        Employee.objects.create(emp_no='E2002', name='Auditor', user=user)
        self.client.force_login(user)  # also raises the AUTH LOGIN signal
        self.reset_offsets()

    def test_create_update_and_delete_are_logged_with_the_actor(self):
        response = self.client.get('/crud/')
        self.assertEqual(response.status_code, 200)

        lines = self.audit_lines()
        self.assertIn('DATA CREATE | model=Orgnization.Department', lines)
        self.assertIn('DATA UPDATE | model=Orgnization.Department', lines)
        self.assertIn('DATA DELETE | model=Orgnization.Department', lines)
        self.assertIn('user=auditor(E2002)', lines)
        self.assertIn('ip=127.0.0.1', lines)
        self.assertIn('path=/crud/', lines)

    def test_update_reports_old_and_new_value(self):
        self.client.get('/crud/')

        lines = self.audit_lines()
        self.assertIn('name: "Logging Test" -> "Logging Test (renamed)"', lines)

    def test_password_values_never_reach_the_audit_log(self):
        self.client.get('/create-user/')

        lines = self.audit_lines()
        self.assertIn('model=auth.User', lines)
        self.assertIn('password=***', lines)
        self.assertNotIn('pbkdf2', lines)
        self.assertNotIn('SuperSecret123!', lines)


@override_settings(ROOT_URLCONF='miniMES.tests.urls_for_logging', DEBUG=False)
class ErrorLoggingTests(LogFileMixin, TestCase):
    def test_uncaught_exception_is_logged(self):
        client = Client(raise_request_exception=False)
        response = client.get('/boom/')
        self.assertEqual(response.status_code, 500)

        lines = self.error_lines()
        self.assertIn('Internal Server Error: /boom/', lines)
        self.assertIn('RuntimeError', lines)
        self.assertIn('logging system smoke test', lines)

    def test_missing_page_is_logged(self):
        client = Client(raise_request_exception=False)
        response = client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)

        lines = self.error_lines()
        self.assertIn('Not Found: /no-such-page/', lines)
        # Django logs the 404 after the middleware chain returns, so the record
        # must still carry the request context.
        self.assertIn('ip=127.0.0.1', lines)

    def test_error_is_attributed_to_the_signed_in_user(self):
        user = get_user_model().objects.create_user(username='erring', password=PASSWORD)
        Employee.objects.create(emp_no='E3003', name='Erring', user=user)
        client = Client(raise_request_exception=False)
        client.force_login(user)
        self.reset_offsets()

        client.get('/no-such-page/')

        lines = self.error_lines()
        self.assertIn('user=erring', lines)
        self.assertIn('ip=127.0.0.1', lines)
