from django.urls import path
from .views import CustomerDashboardView, CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDeleteView, CustomerDetailView, check_customer_id

app_name = 'customer'

urlpatterns = [
    path('', CustomerDashboardView.as_view(), name='customer-dashboard'),
    path('list/', CustomerListView.as_view(), name='customer-list'),
    path('add/', CustomerCreateView.as_view(), name='customer-add'),
    path('<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer-edit'),
    path('<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer-delete'),
    path('check-customer-id/', check_customer_id, name='check-customer-id'),
]
