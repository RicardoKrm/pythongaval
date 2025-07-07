# flota/context_processors.py (CORREGIDO)

from .models import Notificacion
# Se eliminó la importación de 'puede_gestionar_ots' porque ya no existe
from .decorators import es_personal_operativo, es_administrador, es_gerente, es_mecanico

def notificaciones_processor(request):
    if not request.user.is_authenticated:
        return {}

    # El nombre 'es_supervisor_o_admin' se usa en la plantilla, pero llama
    # a nuestra función limpia 'es_personal_operativo' (Admin o Supervisor).
    # Esto es correcto y consistente.
    return {
        'notificaciones_recientes': request.user.notificaciones.all()[:5],
        'notificaciones_no_leidas_count': request.user.notificaciones.filter(leida=False).count(),
        'es_administrador': es_administrador(request.user),
        'es_supervisor_o_admin': es_personal_operativo(request.user),
        'es_gerente': es_gerente(request.user),
        'es_mecanico': es_mecanico(request.user),
        # Se eliminó la línea de 'puede_gestionar_ots' que causaba el error.
    }