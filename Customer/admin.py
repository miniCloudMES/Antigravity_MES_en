from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'name', 'contact_person', 'phone', 'is_active']
    search_fields = ['customer_id', 'name', 'contact_person']
    list_filter = ['is_active']
