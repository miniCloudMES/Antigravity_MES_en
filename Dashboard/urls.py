from django.urls import path
from .views import LandingPageView, DashboardView, dashboard_template_switch

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing-page'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/template-switch/', dashboard_template_switch, name='dashboard-template-switch'),
]
