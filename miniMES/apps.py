"""App config for the project package itself.

``miniMES`` is listed in ``INSTALLED_APPS`` only so that :meth:`ready` runs and
the audit signal receivers get connected at startup.
"""

from django.apps import AppConfig


class MiniMESConfig(AppConfig):
    name = 'miniMES'
    verbose_name = 'miniMES core'

    def ready(self):
        # Importing the module registers every signal receiver (login/logout,
        # create/update/delete, request/response lifecycle).
        from miniMES import audit  # noqa: F401
