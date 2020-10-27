# app/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

app_name = 'app'

urlpatterns = [
    path('', views.index, name='index'),
    path('index_yrno_next12h_data', views.index_yrno_next12h_data, name='index_yrno_next12h_data'),
    path('index_ilmateenistus_now_data', views.index_ilmateenistus_now_data, name='index_ilmateenistus_now_data'),
    # path('container_date_today_24hours', views.container_date_today_24hours, name='container_date_today_24hours'),
    path('ilm/', views.ilm_Ilmateenistus_now, name='ilm_praegu_ilmateenistusest'),
    # path('index_data', views.index_data, name='index_data'),
    path('log/<str:date_string>/', views.log, name='log'),
    path('status/', views.status, name='status'),
    path('today/', views.today, name='today'),
    path('weekly_timer/', views.weekly_timer, name='weekly_timer')
]

# Serve static files
if settings.DEBUG:
   urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
