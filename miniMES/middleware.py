"""Middleware that exposes the active request to the logging system."""

from miniMES.log_context import set_current_request


class RequestAuditMiddleware:
    """Publish the current request to the audit logging thread-local.

    Place this first in ``MIDDLEWARE`` so it wraps every other layer.

    The context is deliberately *not* cleared on the way out: Django logs the
    response itself (``django.request``: "Not Found: ...", "Internal Server
    Error: ...") in ``BaseHandler.get_response``, i.e. only *after* the
    middleware chain has returned.  Clearing here would strip the actor and IP
    from exactly those records.  Instead the context lives until the response
    is closed, when ``request_finished`` clears it (see ``miniMES.audit``), and
    every new request overwrites it on entry.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        return self.get_response(request)
