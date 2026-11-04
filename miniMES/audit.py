"""Audit logging: authentication events and data changes.

Two families of events are written to ``log/miniMES_audit.log``:

* ``AUTH ...``   – login, logout, failed login (with client IP).
* ``DATA ...``   – create / update / delete on every auditable model, with the
  changed fields and their old → new values for updates.

Receivers are connected from :class:`miniMES.apps.MiniMESConfig.ready`.

The actor, IP and request path come from the thread-local set by
``miniMES.middleware.RequestAuditMiddleware``; outside a request the actor is
reported as ``system``.
"""

import logging
import threading

from django.conf import settings
from django.contrib.auth.signals import (
    user_logged_in,
    user_login_failed,
    user_logged_out,
)
from django.core.signals import request_finished
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from miniMES.log_context import (
    clear_current_request,
    current_request_hint,
    describe_user,
    get_client_ip,
)

logger = logging.getLogger('miniMES.audit')

# Infrastructure tables nobody wants in a data-audit trail.  Override with
# settings.AUDIT_IGNORED_MODELS (list of ``app_label.ModelName``).
DEFAULT_IGNORED_MODELS = (
    'sessions.Session',
    'admin.LogEntry',
    'contenttypes.ContentType',
    'auth.Permission',
    'Documents.DocumentAuditLog',
)

# Fields never worth reporting in a diff.
IGNORED_FIELDS = {'last_login'}

# Values that must never reach a log file (matched on the field name).
DEFAULT_SENSITIVE_FIELDS = {
    'password', 'raw_password', 'secret', 'token', 'api_key', 'apikey',
    'private_key', 'access_token', 'refresh_token',
}

MASKED = '***'

_state = threading.local()


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _ignored_models():
    return set(getattr(settings, 'AUDIT_IGNORED_MODELS', DEFAULT_IGNORED_MODELS))


def _should_audit(sender):
    """True when the model behind ``sender`` belongs in the audit trail."""
    meta = getattr(sender, '_meta', None)
    if meta is None:
        return False
    if meta.auto_created:  # auto-generated m2m "through" tables
        return False
    if not meta.managed:  # unmanaged/legacy views
        return False
    return meta.label not in _ignored_models()


def _max_value_length():
    return getattr(settings, 'AUDIT_MAX_VALUE_LENGTH', 200)


def _sensitive_fields():
    return set(getattr(settings, 'AUDIT_SENSITIVE_FIELDS', DEFAULT_SENSITIVE_FIELDS))


def _is_sensitive(name):
    lowered = name.lower()
    return lowered in _sensitive_fields() or any(
        marker in lowered for marker in ('password', 'secret', 'token')
    )


def _format_value(value, limit=None):
    limit = limit or _max_value_length()
    if value is None:
        return 'NULL'
    if isinstance(value, str):
        text = f'"{value}"'
    else:
        text = repr(value)
    if len(text) > limit:
        text = f'{text[:limit]}...(+{len(text) - limit} chars)'
    return text


def _format_fields(instance):
    """``field=value, ...`` summary used for create/delete lines."""
    parts = []
    for field in instance._meta.concrete_fields:
        if field.name in IGNORED_FIELDS:
            continue
        if _is_sensitive(field.name):
            parts.append(f'{field.name}={MASKED}')
            continue
        parts.append(f'{field.name}={_format_value(getattr(instance, field.attname))}')
    return ', '.join(parts)


def _pending_store():
    store = getattr(_state, 'pending_changes', None)
    if store is None:
        store = _state.pending_changes = {}
    return store


def _remember_changes(label, pk, changes):
    _pending_store()[(label, str(pk))] = changes


def _pop_changes(label, pk):
    return _pending_store().pop((label, str(pk)), None)


def _actor_and_origin():
    return describe_user(), get_client_ip(), current_request_hint()


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #
@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    logger.info(
        'AUTH LOGIN | user=%s ip=%s %s',
        describe_user(user), get_client_ip(request), current_request_hint(),
    )


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    logger.info(
        'AUTH LOGOUT | user=%s ip=%s %s',
        describe_user(user), get_client_ip(request), current_request_hint(),
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request=None, **kwargs):
    # credentials may contain the submitted password: log the identifier only.
    username = (credentials or {}).get('username') or (credentials or {}).get('emp_no') or '-'
    logger.warning(
        'AUTH LOGIN_FAILED | username=%s ip=%s %s',
        username, get_client_ip(request), current_request_hint(),
    )


# --------------------------------------------------------------------------- #
# data changes
# --------------------------------------------------------------------------- #
@receiver(pre_save)
def capture_pending_changes(sender, instance, **kwargs):
    """Snapshot the stored row so ``post_save`` can report a field-level diff."""
    if not logger.isEnabledFor(logging.INFO) or not _should_audit(sender):
        return
    if instance.pk is None:  # insert: nothing to compare against
        return
    try:
        old = sender._default_manager.get(pk=instance.pk)
    except Exception:
        return

    changes = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key or field.name in IGNORED_FIELDS:
            continue
        if getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False):
            continue  # timestamps changed by Django itself, not by the user
        old_value = getattr(old, field.attname)
        new_value = getattr(instance, field.attname)
        if old_value != new_value:
            changes[field.name] = (old_value, new_value)

    if changes:
        _remember_changes(sender._meta.label, instance.pk, changes)


@receiver(post_save)
def log_data_save(sender, instance, created, raw=False, **kwargs):
    if raw:  # loaddata / fixtures: not an interactive change
        return
    if not logger.isEnabledFor(logging.INFO) or not _should_audit(sender):
        return

    user, ip, origin = _actor_and_origin()
    label = sender._meta.label

    if created:
        logger.info(
            'DATA CREATE | model=%s pk=%s user=%s ip=%s %s | %s',
            label, instance.pk, user, ip, origin, _format_fields(instance),
        )
        return

    changes = _pop_changes(label, instance.pk)
    if not changes:  # save() that changed nothing: not a data change
        return

    diff = ', '.join(
        f'{name}: {MASKED} (changed)' if _is_sensitive(name)
        else f'{name}: {_format_value(old)} -> {_format_value(new)}'
        for name, (old, new) in changes.items()
    )
    logger.info(
        'DATA UPDATE | model=%s pk=%s user=%s ip=%s %s | %s',
        label, instance.pk, user, ip, origin, diff,
    )


@receiver(post_delete)
def log_data_delete(sender, instance, **kwargs):
    if not logger.isEnabledFor(logging.INFO) or not _should_audit(sender):
        return

    user, ip, origin = _actor_and_origin()
    logger.info(
        'DATA DELETE | model=%s pk=%s user=%s ip=%s %s | %s',
        sender._meta.label, instance.pk, user, ip, origin, _format_fields(instance),
    )


# --------------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------------- #
@receiver(request_finished)
def clear_request_context(sender, **kwargs):
    """Never let a request object leak into the next task on this thread."""
    clear_current_request()
