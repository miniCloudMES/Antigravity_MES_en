from django.urls import path
from .views import (
    ProductionDashboardView,
    WorkOrderListView,
    WorkOrderCreateView,
    WorkOrderUpdateView,
    WorkOrderDeleteView,
    WorkOrderDetailView,
    BOMListView,
    BOMDetailView,
    BOMCreateView,
    BOMUpdateView,
    BOMDeleteView,
    ProcessCardListView,
    ProcessCardDetailView,
    ProcessCardEditView,
    workorder_step_update,
    workorder_step_quantity,
    workorder_step_track_in,
    workorder_step_track_out,
    workorder_picking,
    ProductionReportView,
    check_workorder_number,
    workorder_qrcode,
)

urlpatterns = [
    path('', ProductionDashboardView.as_view(), name='production-dashboard'),
    # WorkOrder
    path('workorders/', WorkOrderListView.as_view(), name='workorder-list'),
    path('workorders/add/', WorkOrderCreateView.as_view(), name='workorder-add'),
    path('workorders/<int:pk>/', WorkOrderDetailView.as_view(), name='workorder-detail'),
    path('workorders/<int:pk>/qrcode/', workorder_qrcode, name='workorder-qrcode'),
    path('workorders/<int:pk>/edit/', WorkOrderUpdateView.as_view(), name='workorder-edit'),
    path('workorders/<int:pk>/delete/', WorkOrderDeleteView.as_view(), name='workorder-delete'),
    path('workorders/check-number/', check_workorder_number, name='check-workorder-number'),
    # BOM
    path('bom/', BOMListView.as_view(), name='bom-list'),
    path('bom/add/', BOMCreateView.as_view(), name='bom-add'),
    path('bom/<int:pk>/', BOMDetailView.as_view(), name='bom-detail'),
    path('bom/<int:pk>/edit/', BOMUpdateView.as_view(), name='bom-edit'),
    path('bom/<int:pk>/delete/', BOMDeleteView.as_view(), name='bom-delete'),
    # Process Cards (Standard Process)
    path('process-cards/', ProcessCardListView.as_view(), name='process-card-list'),
    path('process-cards/<int:pk>/', ProcessCardDetailView.as_view(), name='process-card-detail'),
    path('process-cards/<int:pk>/edit/', ProcessCardEditView.as_view(), name='process-card-edit'),
    # Work Order Steps
    path('workorders/<int:pk>/picking/', workorder_picking, name='workorder-picking'),
    path('workorder-steps/<int:pk>/track-in/', workorder_step_track_in, name='workorder-step-track-in'),
    path('workorder-steps/<int:pk>/track-out/', workorder_step_track_out, name='workorder-step-track-out'),
    path('workorder-steps/<int:pk>/update/', workorder_step_update, name='workorder-step-update'),
    path('workorder-steps/<int:pk>/quantity/', workorder_step_quantity, name='workorder-step-quantity'),
    # Reports
    path('report/', ProductionReportView.as_view(), name='production-report'),
]