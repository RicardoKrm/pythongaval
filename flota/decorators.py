# flota/decorators.py (CORREGIDO Y LIMPIO)

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

def es_administrador(user):
    """Verifica si el usuario está en el grupo 'Administrador'."""
    return user.groups.filter(name='Administrador').exists()

def es_supervisor(user):
    """Verifica si el usuario está en el grupo 'Supervisor'."""
    return user.groups.filter(name='Supervisor').exists()

def es_mecanico(user):
    """Verifica si el usuario está en el grupo 'Mecánico'."""
    return user.groups.filter(name='Mecánico').exists()

def es_gerente(user):
    """Verifica si el usuario está en el grupo 'Gerente'."""
    return user.groups.filter(name='Gerente').exists()

def es_personal_operativo(user):
    """
    Verifica si el usuario tiene un rol operativo activo (Admin, Supervisor).
    Estos son los roles que gestionan el día a día de la plataforma.
    """
    return user.groups.filter(name__in=['Administrador', 'Supervisor']).exists()

# NOTA: Tu función 'puede_gestionar_ots' hacía lo mismo que la definición
# correcta de 'es_personal_operativo', por lo que la he eliminado para
# evitar redundancia y usar un solo nombre consistente.
# Si la usabas en otro lado, puedes simplemente renombrarla.