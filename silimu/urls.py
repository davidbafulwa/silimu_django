from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),   # admin technique Django (facultatif)
    path('api/', include('reservations.api_urls')),
    path('', include('reservations.urls')),
]
