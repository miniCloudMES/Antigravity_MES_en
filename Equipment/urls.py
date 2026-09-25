from django.urls import path
from . import views
from .views import check_equipment_id

urlpatterns = [
    path('dashboard/', views.EquipmentDashboardView.as_view(), name='equipment-dashboard'),
    path('categories/', views.EquipmentCategoryListView.as_view(), name='equipment-category-list'),
    path('categories/add/', views.EquipmentCategoryCreateView.as_view(), name='equipment-category-add'),
    path('categories/<int:pk>/edit/', views.EquipmentCategoryUpdateView.as_view(), name='equipment-category-edit'),
    path('categories/<int:pk>/delete/', views.EquipmentCategoryDeleteView.as_view(), name='equipment-category-delete'),
    
    path('list/', views.EquipmentListView.as_view(), name='equipment-list'),
    path('add/', views.EquipmentCreateView.as_view(), name='equipment-add'),
    path('<int:pk>/edit/', views.EquipmentUpdateView.as_view(), name='equipment-edit'),
    path('<int:pk>/delete/', views.EquipmentDeleteView.as_view(), name='equipment-delete'),
    path('<int:pk>/detail/', views.EquipmentDetailView.as_view(), name='equipment-detail'),
    path('<int:pk>/maintenance/add/', views.MaintenanceRecordCreateView.as_view(), name='maintenance-add'),
    path('check-equipment-id/', check_equipment_id, name='check-equipment-id'),
]
