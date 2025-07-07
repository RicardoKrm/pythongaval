from django.core.exceptions import PermissionDenied

def es_administrador(user):
    """Verifica si el usuario es superusuario o está en el grupo 'Administrador'."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name='Administrador').exists()

def es_supervisor(user):
    """Verifica si el usuario está en el grupo 'Supervisor'."""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Supervisor').exists()

def es_mecanico(user):
    """Verifica si el usuario está en el grupo 'Mecánico'."""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Mecánico').exists()

def es_gerente(user):
    """Verifica si el usuario está en el grupo 'Gerente'."""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Gerente').exists()

def es_personal_operativo(user):
    """
    Verifica si el usuario tiene un rol operativo activo (Superusuario, Admin, Supervisor).
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Administrador', 'Supervisor']).exists()