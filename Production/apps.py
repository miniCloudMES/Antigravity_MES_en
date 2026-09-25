from django.apps import AppConfig


class ProductionConfig(AppConfig):
    name = 'Production'
    default_auto_field = 'django.db.models.BigAutoField'
