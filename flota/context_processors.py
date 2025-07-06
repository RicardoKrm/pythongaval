# Reemplaza el contenido completo de flota/context_processors.py con esto:

from .models import Notificacion
from .decorators import es_personal_operativo, es_administrador, es_gerente, es_mecanico, puede_gestionar_ots

def notificaciones_processor(request):
    if not request.user.is_authenticated:
        return {}

    return {
        'notificaciones_recientes': request.user.notificaciones.all()[:5],
        'notificaciones_no_leidas_count': request.user.notificaciones.filter(leida=False).count(),
        'es_administrador': es_administrador(request.user),
        'es_supervisor_o_admin': es_personal_operativo(request.user), # Mantenemos el nombre anterior por si lo usas
        'puede_gestionar_ots': puede_gestionar_ots(request.user), # Para acciones de gestión
        'es_gerente': es_gerente(request.user),
        'es_mecanico': es_mecanico(request.user),
    }