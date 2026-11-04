"""Views used only by the logging tests (they exercise the audit trail)."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse

from Orgnization.models import Department


def crud_view(request):
    """Create, update and delete one Department and return 200."""
    dept = Department.objects.create(code='LOG-TEST', name='Logging Test')
    dept.name = 'Logging Test (renamed)'
    dept.save()
    dept.delete()
    return HttpResponse('ok')


def user_create_view(request):
    """Create a user with a password, to prove secrets are masked in the log."""
    get_user_model().objects.create_user(
        username='masked-user', password='SuperSecret123!'
    )
    return HttpResponse('ok')


def boom_view(request):
    """Raise, to prove uncaught exceptions reach the error log."""
    raise RuntimeError('logging system smoke test')
