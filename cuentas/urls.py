# cuentas/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views



urlpatterns = [
    # Cuando se visite /login/, se usará la vista de login de Django
    # pero le decimos que renderice NUESTRO template personalizado.
    path('login/', auth_views.LoginView.as_view(template_name='cuentas/login.html'), name='login'),
    
    # La ruta de logout usará la vista por defecto de Django, que no necesita un template.
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]