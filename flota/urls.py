# flota/urls.py


from django.urls import path

from . import views

from . import admin


app_name = 'flota'


urlpatterns = [

    path('dashboard/', views.dashboard_flota, name='dashboard'),

    path('ordenes/', views.orden_trabajo_list, name='ot_list'),

    path('ordenes/<int:pk>/', views.orden_trabajo_detail, name='ot_detail'),

    path('ordenes/<int:pk>/cambiar-estado/', views.cambiar_estado_ot, name='cambiar_estado_ot'),

    path('ordenes/<int:pk>/pdf/', views.generar_ot_pdf, name='generar_ot_pdf'),

    path('bitacora/', views.bitacora_diaria_list, name='bitacora_list'),

    path('indicadores/', views.indicadores_dashboard, name='indicadores_dashboard'),

    path('analisis-fallas/', views.analisis_fallas, name='analisis_fallas'),

    path('analisis-avanzado/', views.analisis_avanzado, name='analisis_avanzado'),

    path('carga-masiva/', views.carga_masiva, name='carga_masiva'),

] 