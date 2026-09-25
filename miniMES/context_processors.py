from Orgnization.models import Employee


def user_role(request):
    result = {
        'user_employee': None,
        'user_role': None,
        'is_admin': False,
        'is_manager': False,
        'is_operator': False,
    }
    user = getattr(request, 'user', None)
    if not user or not user.pk or not user.is_authenticated:
        return result
    try:
        emp = Employee.objects.select_related('department', 'position').get(user=user)
        result['user_employee'] = emp
        result['user_role'] = emp.role
        result['is_admin'] = emp.role == 'admin'
        result['is_manager'] = emp.role in ('manager', 'admin')
        result['is_operator'] = emp.role == 'operator'
    except Employee.DoesNotExist:
        pass
    return result
