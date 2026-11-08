"""Thread-local request context for the logging/audit system.

Model signals (``post_save`` / ``post_delete``) and the logging filter need to
know *who* performed an action and *from which IP*, but signals have no access
to the HTTP request.  ``RequestAuditMiddleware`` stashes the active request
here, so any code running inside that request can look it up.

Outside a request (management commands, shell, scheduled jobs) the context is
empty and actors are reported as ``system``.
"""

import threading

_state = threading.local()


def set_current_request(request):
    """Remember the request being served by the current thread."""
    _state.request = request


def clear_current_request():
    """Forget the request (called when the response is finished)."""
    _state.request = None


def get_current_request():
    """Return the request being served by the current thread, if any."""
    return getattr(_state, 'request', None)


def get_client_ip(request=None):
    """Best-effort client IP, honouring ``X-Forwarded-For`` behind nginx."""
    request = request if request is not None else get_current_request()
    if request is None:
        return '-'
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or '-'


def get_current_user():
    """Return the authenticated user of the current request, or ``None``.

    Resolving ``request.user`` is not free: it reads the session, and Django
    logs "Session data corrupted" when the session cookie cannot be verified
    (rotated ``SECRET_KEY``, stale cookie, tampering).  Our logging filter runs
    on that very record, so evaluating the user from inside the filter used to
    re-enter this function while the first evaluation was still in flight ->
    recursion until ``RecursionError`` -> HTTP 500.  The re-entrancy guard makes
    the nested call return ``None`` instead.

    ``request.user`` is a ``SimpleLazyObject``: ``getattr`` only hands back the
    lazy wrapper, the session is read on the *first attribute access*.  The
    whole evaluation therefore has to stay inside the guard, not just the
    ``getattr``.
    """
    if getattr(_state, 'resolving_user', False):
        return None
    request = get_current_request()
    if request is None:
        return None
    _state.resolving_user = True
    try:
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            return user
        return None
    except Exception:  # a broken session/auth backend must never break logging
        return None
    finally:
        _state.resolving_user = False


def describe_user(user=None):
    """Compact actor label: ``username(emp_no)``.

    Falls back to ``anonymous`` inside a request with no logged-in user, and to
    ``system`` when there is no request at all (cron, management command, ...).
    """
    if user is None:
        user = get_current_user()
    if user is None:
        return 'system' if get_current_request() is None else 'anonymous'
    if not getattr(user, 'is_authenticated', True):
        return 'anonymous'

    label = user.get_username()
    employee = getattr(user, 'employee', None)  # reverse OneToOne, may not exist
    emp_no = getattr(employee, 'emp_no', None)
    if emp_no:
        label = f'{label}({emp_no})'
    return label


def current_request_hint():
    """``path=... method=...`` fragment used in audit lines."""
    request = get_current_request()
    if request is None:
        return 'path=-'
    return 'path=%s method=%s' % (
        getattr(request, 'path', '-'),
        getattr(request, 'method', '-'),
    )
