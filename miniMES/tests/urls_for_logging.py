"""URLconf used only by the logging tests."""

from django.urls import include, path

from miniMES.tests.views_for_logging import (
    boom_view,
    crud_view,
    user_create_view,
    whoami_view,
)

urlpatterns = [
    path('crud/', crud_view, name='test-crud'),
    path('create-user/', user_create_view, name='test-create-user'),
    path('boom/', boom_view, name='test-boom'),
    path('whoami/', whoami_view, name='test-whoami'),
    path('accounts/', include('django.contrib.auth.urls')),
]
