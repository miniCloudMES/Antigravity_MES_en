"""
URL configuration for miniMES project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('Dashboard.urls')),
    path('org/', include('Orgnization.urls')),
    path('equipment/', include('Equipment.urls')),
    path('material/', include('Material.urls')),
    path('product/', include('Product.urls')),
    path('supplier/', include('Supplier.urls')),
    path('production/', include('Production.urls')),
    path('customer/', include('Customer.urls')),
    path('documents/', include('Documents.urls')),
    path('files/', include('FileLibrary.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
