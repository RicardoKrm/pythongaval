from .models import Notificacion
# Importamos las funciones de verificación de roles desde decorators.py
from .decorators import es_personal_operativo, es_administrador

def notificaciones_processor(request):
    """
    Añade información global al contexto de todas las plantillas,
    incluyendo notificaciones y variables de rol.
    """
    if not request.user.is_authenticated:
        return {} # No hacer nada si el usuario no está logueado

    # 1. Lógica de Notificaciones
    notificaciones_recientes = request.user.notificaciones.all()[:5]
    notificaciones_no_leidas_count = request.user.notificaciones.filter(leida=False).count()

    # 2. Lógica de Roles
    # Estas variables estarán disponibles en todas las plantillas como {{ es_administrador }}
    # y {{ es_personal_operativo }}
    
    return {
        'notificaciones_recientes': notificaciones_recientes,
        'notificaciones_no_leidas_count': notificaciones_no_leidas_count,
        'es_administrador': es_administrador(request.user),
        'es_personal_operativo': es_personal_operativo(request.user),
    }