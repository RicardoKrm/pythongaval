from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from flota import views as flota_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='cuentas/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', flota_views.landing_page, name='landing'),
]