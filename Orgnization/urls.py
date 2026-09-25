from django.urls import path
from . import views
from .views import DepartmentListView, DepartmentCreateView, DepartmentUpdateView, DepartmentDeleteView
from .views import PositionListView, PositionCreateView, PositionUpdateView, PositionDeleteView
from .views import EmployeeListView, EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView
from .views import check_emp_no, check_dept_code, check_position_code
from .views import ProfileView

urlpatterns = [
    path('', views.index, name='org-index'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('dashboard/', views.OrgDashboardView.as_view(), name='org-dashboard'),
    path('departments/', DepartmentListView.as_view(), name='department-list'),
    path('departments/add/', DepartmentCreateView.as_view(), name='department-add'),
    path('departments/<int:pk>/edit/', DepartmentUpdateView.as_view(), name='department-edit'),
    path('departments/<int:pk>/delete/', DepartmentDeleteView.as_view(), name='department-delete'),
    
    path('positions/', PositionListView.as_view(), name='position-list'),
    path('positions/add/', PositionCreateView.as_view(), name='position-add'),
    path('positions/<int:pk>/edit/', PositionUpdateView.as_view(), name='position-edit'),
    path('positions/<int:pk>/delete/', PositionDeleteView.as_view(), name='position-delete'),

    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/add/', EmployeeCreateView.as_view(), name='employee-add'),
    path('employees/<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee-edit'),
    path('employees/<int:pk>/delete/', EmployeeDeleteView.as_view(), name='employee-delete'),
    path('employees/check-emp-no/', check_emp_no, name='check-emp-no'),
    path('departments/check-dept-code/', check_dept_code, name='check-dept-code'),
    path('positions/check-position-code/', check_position_code, name='check-position-code'),
    path('employees/<int:pk>/change-password/', views.employee_change_password, name='employee-change-password'),
]
