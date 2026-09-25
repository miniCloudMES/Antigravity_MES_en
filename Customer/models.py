from django.db import models


class Customer(models.Model):
    customer_id = models.CharField(max_length=50, unique=True, verbose_name='Customer ID')
    name = models.CharField(max_length=100, verbose_name='Customer Name')
    contact_person = models.CharField(max_length=50, blank=True, verbose_name='Contact Person')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Phone')
    email = models.EmailField(blank=True, verbose_name='Email')
    address = models.CharField(max_length=200, blank=True, verbose_name='Address')
    tax_id = models.CharField(max_length=20, blank=True, verbose_name='Tax ID')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    notes = models.TextField(blank=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    def __str__(self):
        return f'{self.customer_id} - {self.name}'

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['customer_id']
