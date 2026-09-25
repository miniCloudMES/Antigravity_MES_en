from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import Department, Position, Employee

User = get_user_model()


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'description')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'description')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('emp_no', 'name', 'gender', 'department', 'position', 'role', 'email', 'is_active')
    list_filter = ('role', 'department', 'position', 'is_active')
    search_fields = ('emp_no', 'name', 'email', 'phone')
    raw_id_fields = ('user',)
    autocomplete_fields = ('department', 'position')
    list_select_related = ('department', 'position')


# Embed the Employee record inside the default Django User admin
class EmployeeInline(admin.StackedInline):
    model = Employee
    fk_name = 'user'
    extra = 0
    can_delete = False
    fields = ('emp_no', 'name', 'role', 'department', 'position', 'is_active')


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (EmployeeInline,)
