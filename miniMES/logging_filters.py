"""Logging filters that enrich every record with request information."""

import logging

from miniMES.log_context import (
    get_client_ip,
    get_current_request,
    get_current_user,
)


class RequestContextFilter(logging.Filter):
    """Attach ``user`` / ``ip`` / ``path`` / ``method`` to every log record.

    This is what lets Django's own records (for example ``django.request``
    "Internal Server Error" entries) show who triggered them, without every
    call site having to pass that information explicitly.
    """

    def filter(self, record):
        # Logging must never break a request: an exception raised here travels
        # back through the logging machinery and can turn a 200 into a 500.
        try:
            request = get_current_request()
            user = get_current_user()

            record.user = user.get_username() if user is not None else '-'
            record.ip = get_client_ip(request)
            record.path = getattr(request, 'path', '-') if request is not None else '-'
            record.method = getattr(request, 'method', '-') if request is not None else '-'
        except Exception:
            record.user = getattr(record, 'user', None) or '-'
            record.ip = getattr(record, 'ip', None) or '-'
            record.path = getattr(record, 'path', None) or '-'
            record.method = getattr(record, 'method', None) or '-'
        return True
