from django.urls import path
from . import views
from .views import check_product_id

urlpatterns = [
    path('', views.ProductDashboardView.as_view(), name='product-dashboard'),
    path('dashboard/', views.ProductDashboardView.as_view(), name='product-dashboard-alt'),

    path('categories/', views.ProductCategoryListView.as_view(), name='product-category-list'),
    path('categories/add/', views.ProductCategoryCreateView.as_view(), name='product-category-add'),
    path('categories/<int:pk>/edit/', views.ProductCategoryUpdateView.as_view(), name='product-category-edit'),
    path('categories/<int:pk>/delete/', views.ProductCategoryDeleteView.as_view(), name='product-category-delete'),

    path('list/', views.ProductListView.as_view(), name='product-list'),
    path('add/', views.ProductCreateView.as_view(), name='product-add'),
    path('<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product-edit'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('check-product-id/', check_product_id, name='check-product-id'),

    path('transactions/', views.ProductStockTransactionListView.as_view(), name='product-stock-transaction-list'),
    path('transactions/add/', views.ProductStockTransactionCreateView.as_view(), name='product-stock-transaction-add'),
    path('<int:product_pk>/transaction/add/', views.ProductStockTransactionQuickCreate.as_view(), name='product-quick-transaction'),
]
