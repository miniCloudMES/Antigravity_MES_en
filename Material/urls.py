from django.urls import path
from . import views
from .views import check_material_id

urlpatterns = [
    path('', views.MaterialDashboardView.as_view(), name='material-dashboard'),
    path('dashboard/', views.MaterialDashboardView.as_view(), name='material-dashboard-alt'),

    path('categories/', views.MaterialCategoryListView.as_view(), name='material-category-list'),
    path('categories/add/', views.MaterialCategoryCreateView.as_view(), name='material-category-add'),
    path('categories/<int:pk>/edit/', views.MaterialCategoryUpdateView.as_view(), name='material-category-edit'),
    path('categories/<int:pk>/delete/', views.MaterialCategoryDeleteView.as_view(), name='material-category-delete'),

    path('list/', views.MaterialListView.as_view(), name='material-list'),
    path('add/', views.MaterialCreateView.as_view(), name='material-add'),
    path('<int:pk>/edit/', views.MaterialUpdateView.as_view(), name='material-edit'),
    path('<int:pk>/delete/', views.MaterialDeleteView.as_view(), name='material-delete'),
    path('check-material-id/', check_material_id, name='check-material-id'),

    path('transactions/', views.StockTransactionListView.as_view(), name='stock-transaction-list'),
    path('transactions/add/', views.StockTransactionCreateView.as_view(), name='stock-transaction-add'),
    path('<int:material_pk>/transaction/add/', views.StockTransactionQuickCreate.as_view(), name='material-quick-transaction'),
]
