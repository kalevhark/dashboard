# app/urls.py
from django.urls import path

from . import views

app_name = 'app'

urlpatterns = [
    path('', views.index, name='index'),
    path('get_xaxis_categories', views.get_xaxis_categories, name='get_xaxis_categories'),
    path('get_yrno_forecast', views.get_yrno_forecast, name='get_yrno_forecast'),
    path('get_ilmateenistus_now', views.get_ilmateenistus_now, name='get_ilmateenistus_now'),
    path('get_aquarea_serv_data', views.get_aquarea_serv_data, name='get_aquarea_serv_data'),
    path('get_ezr_data', views.get_ezr_data, name='get_ezr_data'),
    path('ilm/', views.get_ilmateenistus_now, name='ilm'),
    path('get_aquarea_smrt_data_day', views.get_aquarea_smrt_data_day, name='get_aquarea_smrt_data_day'),
    path('get_aquarea_smrt_data_month', views.get_aquarea_smrt_data_month, name='get_aquarea_smrt_data_month'),
    path('get_aquarea_smrt_data_year', views.get_aquarea_smrt_data_year, name='get_aquarea_smrt_data_year'),
    path('get_tuyaapi_data', views.get_tuyaapi_data, name='get_tuyaapi_data'),
    path('ezr/', views.get_ezr_data, name='ezr'),
    path('yrno/', views.get_yrno_forecast, name='yrno'),
    # path('log/<str:date_string>/', views.log, name='log'),
    # path('status/', views.status, name='status'),
    # path('today/', views.today, name='today'),
    # path('weekly_timer/', views.weekly_timer, name='weekly_timer')
]

