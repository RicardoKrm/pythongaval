# flota/context_processors.py (Asegúrate que tenga esta versión)
from .models import Notificacion
from .decorators import es_personal_operativo, es_administrador, es_gerente, es_mecanico, es_supervisor 

def notificaciones_processor(request):
    if not request.user.is_authenticated:
        return {
            'es_mecanico': False, 'es_supervisor': False, 'es_administrador': False,
            'es_gerente': False, 'es_personal_operativo': False, 
            'notificaciones_no_leidas_count': 0, 'notificaciones_recientes_no_leidas': []
        }

    notificaciones_no_leidas_count = Notificacion.objects.filter(usuario_destino=request.user, leida=False).count()
    notificaciones_recientes_no_leidas = Notificacion.objects.filter(usuario_destino=request.user, leida=False).order_by('-fecha_creacion')[:5]

    # Usar nombres de variables diferentes a las funciones importadas
    is_mecanico_flag = es_mecanico(request.user)
    is_supervisor_flag = es_supervisor(request.user)
    is_administrador_flag = es_administrador(request.user)
    is_gerente_flag = es_gerente(request.user)
    is_personal_operativo_flag = es_personal_operativo(request.user)

    return {
        'notificaciones_no_leidas_count': notificaciones_no_leidas_count,
        'notificaciones_recientes_no_leidas': notificaciones_recientes_no_leidas, 
        'es_administrador': is_administrador_flag,
        'es_supervisor': is_supervisor_flag,
        'es_gerente': is_gerente_flag,
        'es_mecanico': is_mecanico_flag,
        'es_personal_operativo': is_personal_operativo_flag,
    }