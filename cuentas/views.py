# cuentas/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required

# ... (tus clases CustomLoginView y CustomLogoutView) ...

# --- ¡AÑADE ESTA FUNCIÓN AL FINAL DEL ARCHIVO! ---
@login_required
def perfil_view(request):
    """
    Muestra la página de perfil del usuario que ha iniciado sesión.
    """
    context = {
        'user': request.user
    }
    # Le decimos a Django que busque el template en 'accounts/perfil.html'
    # Esto es porque tu app_name es 'accounts'. Django a menudo organiza
    # los templates en subcarpetas con el nombre de la app para evitar colisiones.
    # Vamos a seguir esta convención.
    return render(request, 'accounts/perfil.html', context)