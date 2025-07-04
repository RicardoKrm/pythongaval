from .models import Notificacion

def notificaciones_processor(request):
    """
    Añade información sobre las notificaciones del usuario al contexto de todas las plantillas.
    """
    if not request.user.is_authenticated:
        return {} # Si el usuario no está logueado, no hacemos nada.

    # Obtenemos las 5 notificaciones más recientes (leídas o no) para el dropdown
    notificaciones_recientes = request.user.notificaciones.all()[:5]
    
    # Contamos solo las que no han sido leídas para el contador de la campana
    notificaciones_no_leidas_count = request.user.notificaciones.filter(leida=False).count()

    return {
        'notificaciones_recientes': notificaciones_recientes,
        'notificaciones_no_leidas_count': notificaciones_no_leidas_count,
    }