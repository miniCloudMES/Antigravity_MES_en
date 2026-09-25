from django.db import models
from django.urls import reverse
import os
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings


ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('operator', 'Operator'),
]


class Department(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Department Code")
    name = models.CharField(max_length=100, verbose_name="Department Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_absolute_url(self):
        return reverse('department-list')

class Position(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Position Code")
    name = models.CharField(max_length=100, verbose_name="Position Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_absolute_url(self):
        return reverse('position-list')

class Employee(models.Model):
    emp_no = models.CharField(max_length=50, unique=True, verbose_name="Employee ID")
    name = models.CharField(max_length=100, verbose_name="Name")
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')], default='M', verbose_name="Gender")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Department")
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Position")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='operator', verbose_name="Role")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="User Account",
    )
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Phone")
    hire_date = models.DateField(blank=True, null=True, verbose_name="Hire Date")
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True, verbose_name="Photo")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    def __str__(self):
        return f"{self.emp_no} - {self.name}"

    def get_absolute_url(self):
        return reverse('employee-list')

@receiver(post_delete, sender=Employee)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.photo and bool(instance.photo.name):
        if os.path.isfile(instance.photo.path):
            os.remove(instance.photo.path)

@receiver(pre_save, sender=Employee)
def auto_delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_file = Employee.objects.get(pk=instance.pk).photo
    except Employee.DoesNotExist:
        return

    new_file = instance.photo
    if bool(old_file) and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
