# cuentas/urls.py
from django.urls import path
from .views import CustomLoginView, CustomLogoutView

# --- ¡Añade esta importación! ---
from .views import perfil_view 

app_name = 'accounts' # Esto es interesante. El app_name es 'accounts' aunque la carpeta es 'cuentas'. ¡No hay problema, lo respetamos!

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    
    # --- ¡AÑADE ESTA LÍNEA! ---
    path('perfil/', perfil_view, name='perfil'),
]