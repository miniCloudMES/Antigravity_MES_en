from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from Orgnization.models import Employee, Department, Position


class Command(BaseCommand):
    help = 'Bind an existing User to an Employee (fixes the problem where createsuperuser cannot log in)'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='User account to bind (the one created by createsuperuser)')
        parser.add_argument('--emp-no', default='EMP-001', help='Employee number (used for login, default EMP-001)')
        parser.add_argument('--role', default='admin', choices=['admin', 'manager', 'operator'], help='Role (default admin)')
        parser.add_argument('--name', default='', help='Full name (defaults to username)')
        parser.add_argument('--dept', default='D001', help='Department code (created automatically if missing, default D001)')
        parser.add_argument('--dept-name', default='Management Dept.', help='Department name (used when creating automatically)')
        parser.add_argument('--position', default='P001', help='Position code (created automatically if missing, default P001)')
        parser.add_argument('--position-name', default='Management', help='Position name (used when creating automatically)')

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            raise CommandError(f'User "{options["username"]}" not found. Please run createsuperuser first.')

        # Already bound: just report it
        existing = Employee.objects.filter(user=user).first()
        if existing:
            self.stdout.write(self.style.WARNING(
                f'This User is already bound to Employee: {existing.emp_no} ({existing.name}, {existing.role})'
            ))
            self.stdout.write(self.style.SUCCESS(f'Please sign in with employee number "{existing.emp_no}"'))
            return

        if Employee.objects.filter(emp_no=options['emp_no']).exists():
            raise CommandError(f'Employee number "{options["emp_no"]}" is already taken. Use --emp-no to specify another number.')

        dept, _ = Department.objects.get_or_create(
            code=options['dept'],
            defaults={'name': options['dept_name']},
        )
        pos, _ = Position.objects.get_or_create(
            code=options['position'],
            defaults={'name': options['position_name']},
        )

        emp = Employee.objects.create(
            emp_no=options['emp_no'],
            user=user,
            name=options['name'] or user.username,
            department=dept,
            position=pos,
            role=options['role'],
        )
        self.stdout.write(self.style.SUCCESS(
            f'Done: {user.username} → {emp.emp_no} ({emp.name}, {emp.role})'
        ))
        self.stdout.write(self.style.SUCCESS(f'Please sign in with employee number "{emp.emp_no}" and the existing password'))
