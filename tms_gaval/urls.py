# tms_gaval/urls.py
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from flota import views as flota_views
from flota import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='cuentas/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', flota_views.dashboard_flota, name='dashboard'),
    path('ordenes/', flota_views.orden_trabajo_list, name='ot_list'),
    path('ordenes/<int:pk>/', flota_views.orden_trabajo_detail, name='ot_detail'),
    path('ordenes/<int:pk>/cambiar-estado/', flota_views.cambiar_estado_ot, name='cambiar_estado_ot'),
    path('ordenes/<int:pk>/pdf/', flota_views.generar_ot_pdf, name='generar_ot_pdf'),
    path('bitacora/', flota_views.bitacora_diaria_list, name='bitacora_list'),
    path('vehiculo/<int:pk>/actualizar-km/', flota_views.actualizar_km_vehiculo, name='actualizar_km'),
    path('indicadores/', flota_views.indicadores_dashboard, name='indicadores_dashboard'),
    path('analisis-fallas/', flota_views.analisis_fallas, name='analisis_fallas'),
    path('analisis-avanzado/', flota_views.analisis_avanzado, name='analisis_avanzado'),
    path('carga-masiva/', flota_views.carga_masiva, name='carga_masiva'),
    path('vehiculo/<int:pk>/historial/', flota_views.historial_vehiculo, name='historial_vehiculo'),
    path('vehiculo/<int:pk>/actualizar-km/', flota_views.actualizar_km_vehiculo, name='actualizar_km'),
    path('vehiculo/<int:pk>/analisis-km/', views.analisis_km_vehiculo, name='analisis_km_vehiculo'),
    path('orden-trabajo/<int:ot_pk>/eliminar-tarea/<int:tarea_pk>/', views.eliminar_tarea_ot, name='eliminar_tarea_ot'),
    path('orden-trabajo/<int:ot_pk>/eliminar-insumo/<int:detalle_pk>/', views.eliminar_insumo_ot, name='eliminar_insumo_ot'),

    
]