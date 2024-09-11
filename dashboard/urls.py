# dashboard/urls.py
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from app import views as appviews

urlpatterns = [
    path('', appviews.index, name='index'),
    path('app/', include('app.urls')),
    path('chat/', include('chat.urls')),
    path('admin/', admin.site.urls),
]

# Serve static files
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)