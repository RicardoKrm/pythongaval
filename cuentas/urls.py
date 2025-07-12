# cuentas/urls.py
from django.urls import path
from .views import CustomLoginView, CustomLogoutView

# --- ¡Añade esta importación! ---
from .views import perfil_view 

app_name = 'cuentas'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    
    # --- ¡AÑADE ESTA LÍNEA! ---
    path('perfil/', perfil_view, name='perfil'),
]