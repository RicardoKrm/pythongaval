from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

def es_administrador(user):
    return user.groups.filter(name='Administrador').exists()

def es_supervisor(user):
    return user.groups.filter(name='Supervisor').exists()

def es_mecanico(user):
    return user.groups.filter(name='Mecánico').exists()

def es_gerente(user):
    return user.groups.filter(name='Gerente').exists()

# Esta función la usaremos mucho
def es_personal_operativo(user):
    """Verifica si el usuario es Admin, Supervisor o Gerente."""
    return user.groups.filter(name__in=['Administrador', 'Supervisor', 'Gerente']).exists()

def es_personal_operativo(user):
    """Verifica si el usuario es Admin o Supervisor (los que operan el día a día)."""
    return user.groups.filter(name__in=['Administrador', 'Supervisor']).exists()

# Añade esta función al final de flota/decorators.py

def puede_gestionar_ots(user):
    """Verifica si el usuario puede gestionar activamente OTs (crear, pausar, asignar).
       Esto excluye al Gerente."""
    return user.groups.filter(name__in=['Administrador', 'Supervisor']).exists()