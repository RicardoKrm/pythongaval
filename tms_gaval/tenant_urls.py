from django.urls import path, include

urlpatterns = [
    path('', include('flota.urls', namespace='flota')),
    path('cuentas/', include('cuentas.urls', namespace='cuentas')),
]
