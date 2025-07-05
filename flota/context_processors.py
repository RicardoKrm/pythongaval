from .models import Notificacion

def notificaciones_processor(request):
    """
    Añade información global al contexto de todas las plantillas.
    """
    if not request.user.is_authenticated:
        return {} # Si el usuario no está logueado, no hacemos nada.

    # 1. Lógica de Notificaciones (existente)
    notificaciones_recientes = request.user.notificaciones.all()[:5]
    notificaciones_no_leidas_count = request.user.notificaciones.filter(leida=False).count()

    # 2. Lógica para verificar si el usuario es Administrador (¡NUEVO!)
    es_administrador = request.user.groups.filter(name='Administrador').exists()

    # 3. Devolvemos todo en el contexto
    return {
        'notificaciones_recientes': notificaciones_recientes,
        'notificaciones_no_leidas_count': notificaciones_no_leidas_count,
        'es_administrador': es_administrador, # <-- Nueva variable disponible en todas las plantillas
    }