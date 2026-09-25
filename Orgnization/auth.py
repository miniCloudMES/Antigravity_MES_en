from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from Orgnization.models import Employee

UserModel = get_user_model()


class EmployeeNoBackend(ModelBackend):
    """
    Allows signing in with an employee number (emp_no).
    The front-end login form still posts a field named "username"; the value is treated here as emp_no.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        emp_no = (username or kwargs.get('emp_no') or '').strip()
        if not emp_no or not password:
            return None
        try:
            emp = Employee.objects.select_related('user').get(emp_no=emp_no)
        except Employee.DoesNotExist:
            return None
        user = getattr(emp, 'user', None)
        if not user or not self.user_can_authenticate(user):
            return None
        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
