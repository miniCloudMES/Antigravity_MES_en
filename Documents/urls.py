from django.urls import path
from . import views

urlpatterns = [
    # Document urls
    path('', views.documents_dashboard, name='documents-dashboard'),
    path('document/new/', views.document_create, name='document-create'),
    path('document/<int:pk>/edit/', views.document_edit, name='document-edit'),
    path('document/<int:pk>/delete/', views.document_delete, name='document-delete'),
    path('document/<int:pk>/submit/', views.document_submit, name='document-submit'),
    path('document/<int:pk>/review/', views.document_review, name='document-review'),
    path('document/<int:pk>/recall/', views.document_recall, name='document-recall'),
    path('document/<int:pk>/toggle-active/', views.document_toggle_active, name='document-toggle-active'),
    path('document/<int:pk>/', views.document_detail, name='document-detail'),
    path('document/<int:pk>/audit-logs/', views.document_audit_logs, name='document-audit-logs'),
    path('document/check-code/', views.check_doc_code, name='check-doc-code'),
    path('document/load-department-reviewers/', views.load_department_reviewers, name='load-department-reviewers'),
    path('audit-logs/', views.audit_dashboard, name='audit-dashboard'),
    
    # Category urls
    path('categories/', views.category_list, name='category-list'),
    path('category/new/', views.category_create, name='category-create'),
    path('category/<int:pk>/edit/', views.category_edit, name='category-edit'),
    path('category/<int:pk>/delete/', views.category_delete, name='category-delete'),
]
