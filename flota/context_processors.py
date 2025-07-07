from .models import Notificacion
from .decorators import es_personal_operativo, es_administrador, es_gerente, es_mecanico

def notificaciones_processor(request):
    if not request.user.is_authenticated:
        return {}
        
    return {
        'notificaciones_no_leidas_count': request.user.notificaciones.filter(leida=False).count(),
        'es_administrador': es_administrador(request.user),
        'es_personal_operativo': es_personal_operativo(request.user),
        'es_gerente': es_gerente(request.user),
        'es_mecanico': es_mecanico(request.user),
    }