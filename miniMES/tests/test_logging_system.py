"""Tests for the file-based logging system.

They assert on the log files themselves, which is the only honest way to prove
that login/logout, data changes and system errors are really written.
"""

import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from Orgnization.models import Employee

LOG_DIR = Path(settings.LOG_DIR)
AUDIT_LOG = LOG_DIR / 'miniMES_audit.log'
ERROR_LOG = LOG_DIR / 'miniMES_error.log'
INFO_LOG = LOG_DIR / 'miniMES_info.log'

PASSWORD = 'Str0ng-Pass!234'
SESSION_KEY = 'a' * 32


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
class CorruptSessionTests(LogFileMixin, TestCase):
    """An unverifiable session cookie must never take the site down.

    Django logs "Session data corrupted" while decoding such a cookie.  Because
    the logging filter resolves ``request.user``, that record used to re-enter
    user resolution while the first one was still running: ~530 frames later the
    request died with ``RecursionError`` and answered HTTP 500.
    """

    def test_corrupt_session_cookie_does_not_500(self):
        Session.objects.create(
            session_key=SESSION_KEY,
            session_data='broken-not-a-signed-payload',
            expire_date=timezone.now() + timedelta(days=1),
        )
        # Send the cookie through the client's jar: an HTTP_COOKIE kwarg is
        # clobbered by the jar, which would silently test nothing.
        self.client.cookies[settings.SESSION_COOKIE_NAME] = SESSION_KEY
        response = self.client.get('/whoami/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AnonymousUser', response.content)

    def test_user_resolution_is_not_re_entered_by_logging(self):
        """The guard itself, pinned deterministically.

        Mirrors what Django really does: ``request.user`` hands back a lazy
        object, and reading an attribute off it is what loads the session — and
        a session that cannot be verified makes Django emit a log record at
        that very moment.  If the logging filter then evaluates the user again,
        resolution re-enters itself until ``RecursionError`` (HTTP 500).
        """
        from miniMES import log_context

        calls = []

        class LazyUser:
            """``request.user``-like: resolving it emits a log record."""

            def _evaluate(self):
                calls.append(1)
                if len(calls) > 50:
                    raise RecursionError('request.user resolution re-entered')
                logging.getLogger('django.security.SuspiciousSession').warning(
                    'nested record emitted while resolving the user'
                )

            @property
            def is_authenticated(self):
                self._evaluate()
                return False

        class RecordEmittingRequest:
            META = {}
            path = '/probe/'
            method = 'GET'

            @property
            def user(self):
                return LazyUser()  # deliberately NOT resolved yet

        log_context.set_current_request(RecordEmittingRequest())
        try:
            user = log_context.get_current_user()
        finally:
            log_context.clear_current_request()

        self.assertIsNone(user)
        self.assertEqual(
            len(calls), 1, 'user resolution must not be re-entered by a log record'
        )


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
