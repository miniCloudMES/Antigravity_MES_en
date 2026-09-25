from django.urls import path
from . import views
from .views import check_supplier_id

urlpatterns = [
    path('', views.SupplierDashboardView.as_view(), name='supplier-dashboard'),
    path('dashboard/', views.SupplierDashboardView.as_view(), name='supplier-dashboard-alt'),
    path('list/', views.SupplierListView.as_view(), name='supplier-list'),
    path('add/', views.SupplierCreateView.as_view(), name='supplier-add'),
    path('<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier-edit'),
    path('<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier-delete'),
    path('check-supplier-id/', check_supplier_id, name='check-supplier-id'),
    # Category
    path('categories/', views.SupplierCategoryListView.as_view(), name='supplier-category-list'),
    path('categories/add/', views.SupplierCategoryCreateView.as_view(), name='supplier-category-add'),
    path('categories/<int:pk>/edit/', views.SupplierCategoryUpdateView.as_view(), name='supplier-category-edit'),
    path('categories/<int:pk>/delete/', views.SupplierCategoryDeleteView.as_view(), name='supplier-category-delete'),
]
