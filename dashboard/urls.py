# dashboard/urls.py
from django.conf.urls import include
from django.urls import path
from django.contrib import admin

urlpatterns = [
    path('app/', include('app.urls')),
    path('chat/', include('chat.urls')),
    path('admin/', admin.site.urls),
]