# flota/views.py

import json
import random
from datetime import datetime, timedelta
import re
import pandas as pd
from weasyprint import HTML

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.db.models import Min, Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Min, Sum, Count, F, Q, Avg
from django.db.models import OuterRef, Subquery, Avg
from django.contrib.auth.models import User, Group
from .decorators import es_personal_operativo
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.db.models import Sum, Count, F, Q # Asegúrate de que todas estas estén
from .decorators import es_administrador, es_gerente # Importamos los decoradores de rol
from datetime import timedelta # Para manejar fechas
from django.db.models.functions import TruncMonth
import csv
from django.http import HttpResponse

from .models import (
    Vehiculo, PautaMantenimiento, OrdenDeTrabajo, BitacoraDiaria, ModeloVehiculo,
    Tarea, Insumo, TipoFalla, Proveedor, DetalleInsumoOT, HistorialOT, Repuesto,
    MovimientoStock, RepuestoRequeridoPorTarea,
    Ruta, CondicionAmbiental, CargaCombustible, transaction, transaction, NormaEuro, Notificacion,
    ConfiguracionEmpresa
    
)
from .forms import (
    OrdenDeTrabajoForm, CambiarEstadoOTForm, BitacoraDiariaForm, CargaMasivaForm, 
    CerrarOtMecanicoForm, AsignarPersonalOTForm, ManualTareaForm, ManualInsumoForm, FiltroPizarraForm, AsignarTareaForm,
    PausarOTForm, DiagnosticoEvaluacionForm, OTFiltroForm, CalendarioFiltroForm, RepuestoForm, MovimientoStockForm, CargaCombustibleForm,
     UsuarioCreacionForm, UsuarioEdicionForm

)
from django.utils import timezone 


def landing_page(request):
    """
    Vista para la landing page pública del sitio.
    """
    # Esta vista simplemente renderiza una plantilla HTML. No necesita contexto.
    return render(request, 'flota/landing.html')

# --- Función de chequeo de rol ---
def es_supervisor_o_admin(user):
    return user.groups.filter(name__in=['Supervisor', 'Administrador']).exists()


@login_required
def dashboard_flota(request):
    """
    Dashboard principal (Pizarra de Mantenimiento).
    Ahora incluye una lógica de redirección al principio para los mecánicos.
    """
    # === INICIO DEL CAMBIO: REDIRECCIÓN POR ROL ===
    # Verificamos si el usuario actual pertenece al grupo 'Mecánico'.
    if request.user.groups.filter(name='Mecánico').exists():
        # Si es un mecánico, no debe ver este dashboard.
        # Lo redirigimos a su lista de OTs, que es su verdadero panel principal.
        return redirect('ot_list')
    # === FIN DEL CAMBIO ===

    # El resto de la función solo se ejecutará si el usuario NO es un mecánico.
    connection.set_tenant(request.tenant)
    
    porcentaje_alerta = 90

    vehiculos_qs = Vehiculo.objects.select_related('modelo', 'norma_euro').order_by('numero_interno')
    filtro_form = FiltroPizarraForm(request.GET or None)
    
    if filtro_form.is_valid():
        if filtro_form.cleaned_data.get('modelo'):
            vehiculos_qs = vehiculos_qs.filter(modelo=filtro_form.cleaned_data['modelo'])
    
    data_flota_completa = []
    costo_total_acumulado = 0
    km_total_flota = 0

    for vehiculo in vehiculos_qs:
        km_actual = vehiculo.kilometraje_actual
        estado = "NORMAL"
        pauta_obj, proximo_km_pauta, kms_faltantes, intervalo_km, fecha_prox_mant = None, None, None, None, None
        
        ultima_ot_preventiva = OrdenDeTrabajo.objects.filter(vehiculo=vehiculo, tipo='PREVENTIVA', estado='FINALIZADA').order_by('-fecha_cierre').first()
        km_ultimo_mant = ultima_ot_preventiva.kilometraje_cierre if ultima_ot_preventiva else None
        fecha_ultimo_mant = ultima_ot_preventiva.fecha_cierre if ultima_ot_preventiva else None
        tipo_ultimo_mant = ultima_ot_preventiva.pauta_mantenimiento.nombre if ultima_ot_preventiva and ultima_ot_preventiva.pauta_mantenimiento else None
        
        proxima_pauta_agg = PautaMantenimiento.objects.filter(modelo_vehiculo=vehiculo.modelo, kilometraje_pauta__gt=km_actual).aggregate(proximo_km=Min('kilometraje_pauta'))
        proximo_km_pauta = proxima_pauta_agg.get('proximo_km')

        if proximo_km_pauta:
            try:
                pauta_obj = PautaMantenimiento.objects.get(modelo_vehiculo=vehiculo.modelo, kilometraje_pauta=proximo_km_pauta)
                intervalo_km = getattr(pauta_obj, 'intervalo_km', 0)
                kms_faltantes = proximo_km_pauta - km_actual
                umbral_vencido = 2000
                umbral_proximo = (intervalo_km * porcentaje_alerta / 100) if intervalo_km > 0 else 5000
                if kms_faltantes <= umbral_vencido: estado = "VENCIDO"
                elif kms_faltantes <= umbral_proximo: estado = "PROXIMO"
            except PautaMantenimiento.DoesNotExist: pass

        ot_abierta = OrdenDeTrabajo.objects.filter(vehiculo=vehiculo).exclude(estado='FINALIZADA').order_by('-fecha_creacion').first()
        km_prom_dia = random.randint(50, 250)
        
        if kms_faltantes and kms_faltantes > 0 and km_prom_dia > 0:
            dias_para_pauta = kms_faltantes / km_prom_dia
            fecha_prox_mant = datetime.now().date() + timedelta(days=dias_para_pauta)

        costo_vehiculo = OrdenDeTrabajo.objects.filter(vehiculo=vehiculo, estado='FINALIZADA').aggregate(total=Sum('costo_total'))['total'] or 0
        costo_total_acumulado += costo_vehiculo
        km_total_flota += km_actual
        
        data_flota_completa.append({
            'vehiculo': vehiculo, 'proxima_pauta_obj': pauta_obj, 'proximo_km': proximo_km_pauta,
            'kms_faltantes': kms_faltantes, 'estado': estado, 'km_prom_dia': km_prom_dia,
            'fecha_prox_mant': fecha_prox_mant, 'intervalo_km': intervalo_km, 'km_ultimo_mant': km_ultimo_mant,
            'fecha_ultimo_mant': fecha_ultimo_mant, 'tipo_ultimo_mant': tipo_ultimo_mant,
            'km_acum_prox': kms_faltantes, 'ot_abierta': ot_abierta,
        })

    data_flota_filtrada = data_flota_completa
    if filtro_form.is_valid():
        tipo_mant = filtro_form.cleaned_data.get('tipo_mantenimiento')
        proximos_5000 = filtro_form.cleaned_data.get('proximos_5000_km')

        if tipo_mant:
            data_flota_filtrada = [item for item in data_flota_filtrada if item['proxima_pauta_obj'] and item['proxima_pauta_obj'].nombre == tipo_mant]
        if proximos_5000:
            data_flota_filtrada = [item for item in data_flota_filtrada if item['kms_faltantes'] is not None and item['kms_faltantes'] <= 5000]

    total_vehiculos_flota = len(data_flota_completa)
    total_vehiculos_filtrados = len(data_flota_filtrada)
    porcentaje_filtrado = (total_vehiculos_filtrados / total_vehiculos_flota * 100) if total_vehiculos_flota > 0 else 0
    costo_por_km = (costo_total_acumulado / km_total_flota) if km_total_flota > 0 else 0

    context = {
        'data_flota': data_flota_filtrada,
        'tenant_name': request.tenant.nombre,
        'filtro_form': filtro_form,
        'kpi_total_filtrado': total_vehiculos_filtrados,
        'kpi_porcentaje_flota': porcentaje_filtrado,
        'kpi_costo_total': costo_total_acumulado,
        'kpi_costo_km': costo_por_km,
    }
    return render(request, 'flota/dashboard.html', context)

@login_required
def orden_trabajo_list(request):
    connection.set_tenant(request.tenant)
    
    # --- Lógica de Creación de OT (sin cambios, pero movida arriba para claridad) ---
    if request.method == 'POST':
        # Solo personal operativo puede crear OTs
        if not es_personal_operativo(request.user):
            raise PermissionDenied # O mostrar un mensaje de error

        form = OrdenDeTrabajoForm(request.POST)
        if form.is_valid():
            ot = form.save(commit=False)
            ot.creada_por = request.user # Opcional: registrar quién creó la OT
            ot.save()
            
            HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='CREACION', descripcion=f"OT #{ot.folio} creada.")
            messages.success(request, f'Orden de Trabajo #{ot.folio} creada con éxito.')
            return redirect('ot_list')
        else:
            messages.error(request, 'Por favor, corrija los errores en el formulario de creación.')
    
    # --- Lógica de Listado y Filtrado (AQUÍ ESTÁ EL CAMBIO PRINCIPAL) ---
    
    # 1. Determinar el queryset base según el rol del usuario
    if es_personal_operativo(request.user):
        # Admins, Supervisores y Gerentes ven todas las OTs
        ordenes_list = OrdenDeTrabajo.objects.all()
    else:
        # Mecánicos ven solo las OTs donde están asignados
        ordenes_list = OrdenDeTrabajo.objects.filter(
            Q(responsable=request.user) | Q(personal_asignado=request.user)
        ).distinct()

    # 2. Aplicar filtros de búsqueda sobre el queryset base
    filtro_form = OTFiltroForm(request.GET)
    if filtro_form.is_valid():
        if filtro_form.cleaned_data['vehiculo']:
            ordenes_list = ordenes_list.filter(vehiculo=filtro_form.cleaned_data['vehiculo'])
        if filtro_form.cleaned_data['tipo']:
            ordenes_list = ordenes_list.filter(tipo=filtro_form.cleaned_data['tipo'])
        if filtro_form.cleaned_data['estado']:
            ordenes_list = ordenes_list.filter(estado=filtro_form.cleaned_data['estado'])
        if filtro_form.cleaned_data['fecha_desde']:
            ordenes_list = ordenes_list.filter(fecha_creacion__date__gte=filtro_form.cleaned_data['fecha_desde'])
        if filtro_form.cleaned_data['fecha_hasta']:
            ordenes_list = ordenes_list.filter(fecha_creacion__date__lte=filtro_form.cleaned_data['fecha_hasta'])

    # 3. Ordenar y Paginar el resultado final
    ordenes_list = ordenes_list.select_related('vehiculo').order_by('-fecha_creacion')
    paginator = Paginator(ordenes_list, 10)
    page = request.GET.get('page')
    try:
        ordenes_paginadas = paginator.page(page)
    except PageNotAnInteger:
        ordenes_paginadas = paginator.page(1)
    except EmptyPage:
        ordenes_paginadas = paginator.page(paginator.num_pages)
    
    # 4. Preparar el formulario de creación para el contexto
    form = OrdenDeTrabajoForm()
    
    context = {
        'ordenes': ordenes_paginadas,
        'form': form,
        'filtro_form': filtro_form,
    }
    return render(request, 'flota/orden_trabajo_list.html', context)

@login_required
def ot_eventos_api(request):
    """
    Devuelve las OTs en formato JSON para FullCalendar, usando fecha_programada
    y permitiendo filtrado.
    """
    connection.set_tenant(request.tenant)
    
    ordenes_qs = OrdenDeTrabajo.objects.all().select_related('vehiculo', 'responsable').prefetch_related('tareas_realizadas__repuestos_requeridos__repuesto')
    
    # Lógica de filtros (sin cambios)
    vehiculo_id = request.GET.get('vehiculo')
    estado = request.GET.get('estado')
    responsable_id = request.GET.get('responsable')
    repuestos_disponibles_filter = request.GET.get('repuestos_disponibles')

    if vehiculo_id:
        ordenes_qs = ordenes_qs.filter(vehiculo_id=vehiculo_id)
    if estado:
        ordenes_qs = ordenes_qs.filter(estado=estado)
    if responsable_id:
        ordenes_qs = ordenes_qs.filter(responsable_id=responsable_id)

    ordenes_filtradas_por_db = list(ordenes_qs) 

    final_ordenes = []
    if repuestos_disponibles_filter == 'true':
        final_ordenes = [ot for ot in ordenes_filtradas_por_db if ot.has_all_parts_available()]
    elif repuestos_disponibles_filter == 'false':
        final_ordenes = [ot for ot in ordenes_filtradas_por_db if not ot.has_all_parts_available()]
    else:
        final_ordenes = ordenes_filtradas_por_db

    eventos = []
    for ot in final_ordenes:
        fecha_inicio_evento = ot.fecha_programada if ot.fecha_programada else ot.fecha_creacion.date()
        
        color = {'PENDIENTE': '#dd6b20', 'EN_PROCESO': '#3182ce', 'PAUSADA': '#d69e2e', 'CERRADA_MECANICO': '#718096', 'FINALIZADA': '#2f855a'}.get(ot.estado, '#718096')
        
        eventos.append({
            'id': ot.pk,
            # --- ¡CAMBIO CLAVE AQUÍ! ---
            # El título ahora es solo el número de la OT.
            'title': f"OT-{ot.folio or ot.pk}", 
            
            'resourceId': ot.responsable_id, 
            'start': fecha_inicio_evento.isoformat(),
            'end': ot.fecha_cierre.isoformat() if ot.fecha_cierre else None, 
            'url': reverse('ot_detail', args=[ot.pk]),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'tipo': ot.get_tipo_display(),
                'estado': ot.get_estado_display(),
                'responsable': ot.responsable.username if ot.responsable else 'N/A',
                # Guardamos el título completo en extendedProps por si lo necesitamos en el tooltip
                'fullTitle': f"OT-{ot.folio or ot.pk} ({ot.vehiculo.numero_interno})", 
                'vehiculo_patente': ot.vehiculo.patente,
                'hasAllPartsAvailable': ot.has_all_parts_available(),
            }
        })
            
    return JsonResponse(eventos, safe=False)

@login_required
def orden_trabajo_detail(request, pk):
    connection.set_tenant(request.tenant)
    ot = get_object_or_404(OrdenDeTrabajo, pk=pk)
    
    # --- LÓGICA DE PERMISOS SIMPLE Y DIRECTA ---
    user_groups = set(request.user.groups.values_list('name', flat=True))
    
    es_mecanico = 'Mecánico' in user_groups
    es_supervisor = 'Supervisor' in user_groups
    es_administrador = 'Administrador' in user_groups

    # PERMISO 1: Supervisores y Admins pueden gestionar tareas y personal.
    puede_gestionar_tareas_y_personal = es_supervisor or es_administrador
    
    # PERMISO 2: SOLO el Administrador puede realizar acciones críticas.
    puede_realizar_acciones_criticas = es_administrador
    # --- FIN DE LA LÓGICA DE PERMISOS ---
    
    # Inicialización de todos los formularios
    asignar_form = AsignarPersonalOTForm(instance=ot)
    cerrar_mecanico_form = CerrarOtMecanicoForm(instance=ot)
    cambiar_estado_form = CambiarEstadoOTForm(instance=ot)
    manual_insumo_form = ManualInsumoForm()
    pausar_form = PausarOTForm(instance=ot)
    diagnostico_form = DiagnosticoEvaluacionForm(instance=ot)
    asignar_tarea_form = AsignarTareaForm()

    if request.method == 'POST':
        if 'cargar_tareas_pauta' in request.POST:
            if ot.tipo == 'PREVENTIVA' and ot.pauta_mantenimiento:
                tareas_de_pauta = ot.pauta_mantenimiento.tareas.all()
                ot.tareas_realizadas.add(*tareas_de_pauta)
                HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='MODIFICACION', descripcion=f"Se cargaron {tareas_de_pauta.count()} tareas desde la pauta '{ot.pauta_mantenimiento.nombre}'.")
                messages.success(request, f"Tareas de la pauta '{ot.pauta_mantenimiento.nombre}' cargadas con éxito.")
            else:
                messages.error(request, "Esta acción solo es válida para OTs Preventivas con una pauta asignada.")
            return redirect('ot_detail', pk=ot.pk)

        elif 'pausar_ot' in request.POST:
            if not puede_realizar_acciones_criticas:
                messages.error(request, "Solo un Administrador puede pausar la OT.")
                return redirect('ot_detail', pk=ot.pk)
            
            form = PausarOTForm(request.POST, instance=ot)
            if form.is_valid():
                instancia = form.save(commit=False)
                instancia.estado = 'PAUSADA'
                instancia.save()

                detalle_pausa = f"Motivo: {instancia.get_motivo_pausa_display()}. Notas: {instancia.notas_pausa or 'N/A'}"
                HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='PAUSA', descripcion=detalle_pausa)
                messages.warning(request, f'La OT #{ot.folio} ha sido pausada con éxito.')
                
                try:
                    # ================== INICIO DEL BLOQUE DE DEBUG ==================
                    print("\n--- DEBUG: INICIANDO BÚSQUEDA DE DESTINATARIOS ---")
                    
                    usuario_actual = request.user
                    print(f"Usuario actual que pausa la OT: {usuario_actual.username} (ID: {usuario_actual.pk})")

                    # Buscamos a TODOS los supervisores y administradores
                    todos_los_gestores = User.objects.filter(
                        Q(groups__name='Supervisor') | Q(groups__name='Administrador')
                    ).distinct()
                    print(f"Gestores encontrados ANTES de excluir: {list(todos_los_gestores)}")

                    # Excluimos al usuario actual
                    destinatarios = todos_los_gestores.exclude(pk=usuario_actual.pk)
                    print(f"Destinatarios finales DESPUÉS de excluir: {list(destinatarios)}")
                    # =================== FIN DEL BLOQUE DE DEBUG ====================
                    
                    if destinatarios.exists():
                        mensaje_notificacion = f"OT #{instancia.folio} ({instancia.vehiculo.numero_interno}) pausada por {request.user.username}."
                        url_notificacion = reverse('ot_detail', args=[ot.pk])
                        
                        notificaciones_a_crear = [
                            Notificacion(usuario_destino=destinatario, mensaje=mensaje_notificacion, url_destino=url_notificacion) 
                            for destinatario in destinatarios
                        ]
                        
                        Notificacion.objects.bulk_create(notificaciones_a_crear)
                        messages.info(request, f"Se ha enviado una notificación a {destinatarios.count()} supervisor(es)/administrador(es).")
                    else:
                        messages.warning(request, "La OT ha sido pausada, pero no se encontraron otros gestores para notificar.")

                except Exception as e:
                    messages.error(request, f"La OT ha sido pausada, pero ocurrió un error al crear las notificaciones: {e}")
                
                return redirect('ot_detail', pk=ot.pk)
            else:
                pausar_form = form

        elif 'guardar_diagnostico' in request.POST:
            form = DiagnosticoEvaluacionForm(request.POST, instance=ot)
            if form.is_valid():
                instancia = form.save()
                HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='MODIFICACION', descripcion=f"Se añadió/actualizó el diagnóstico: '{instancia.diagnostico_evaluacion}'")
                messages.success(request, 'Diagnóstico guardado con éxito.')
                return redirect('ot_detail', pk=ot.pk)
            else:
                diagnostico_form = form
        
        elif 'asignar_tarea_existente' in request.POST:
            form = AsignarTareaForm(request.POST)
            if form.is_valid():
                tarea_seleccionada = form.cleaned_data['tarea']
                if ot.tareas_realizadas.filter(pk=tarea_seleccionada.pk).exists():
                    messages.warning(request, f'La tarea "{tarea_seleccionada.descripcion}" ya está asignada a esta OT.')
                else:
                    ot.tareas_realizadas.add(tarea_seleccionada)
                    HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='MODIFICACION', descripcion=f"Se añadió la tarea: '{tarea_seleccionada.descripcion}'.")
                    messages.success(request, f'Tarea "{tarea_seleccionada.descripcion}" añadida con éxito.')
                return redirect('ot_detail', pk=ot.pk)
            else:
                asignar_tarea_form = form

        elif 'add_manual_insumo' in request.POST:
            form = ManualInsumoForm(request.POST)
            if form.is_valid():
                nombre = form.cleaned_data['nombre']
                precio = form.cleaned_data['precio_unitario']
                cantidad = form.cleaned_data['cantidad']
                insumo, created = Insumo.objects.get_or_create(nombre=nombre, defaults={'precio_unitario': precio})
                DetalleInsumoOT.objects.create(orden_de_trabajo=ot, insumo=insumo, cantidad=cantidad, repuesto_inventario=None)
                messages.success(request, f'Insumo manual "{nombre}" añadido con éxito.')
                return redirect('ot_detail', pk=ot.pk)
            else:
                manual_insumo_form = form

        elif 'asignar_personal' in request.POST:
            form = AsignarPersonalOTForm(request.POST, instance=ot)
            if form.is_valid():
                form.save()
                responsable = form.cleaned_data.get('responsable')
                ayudantes = ", ".join([user.username for user in form.cleaned_data.get('personal_asignado').all()])
                descripcion = f"Se asignó a {responsable.username if responsable else 'nadie'} como responsable. Ayudantes: {ayudantes or 'ninguno'}."
                HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='ASIGNACION', descripcion=descripcion)
                messages.success(request, '¡Personal asignado con éxito!')
                return redirect('ot_detail', pk=ot.pk)
            else:
                asignar_form = form
        
        elif 'cambiar_estado' in request.POST:
            form = CambiarEstadoOTForm(request.POST, instance=ot)
            if form.is_valid():
                nuevo_estado = form.cleaned_data['estado']
                
                if ot.estado == 'PAUSADA' and nuevo_estado == 'EN_PROCESO':
                    ot.motivo_pausa, ot.notas_pausa = None, ""
                    HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='REANUDACION', descripcion="La OT ha sido reanudada y puesta 'En Proceso'.")

                if nuevo_estado == 'FINALIZADA' and ot.estado != 'FINALIZADA':
                    ot.fecha_cierre = timezone.now()
                    duracion_total = ot.fecha_cierre - ot.fecha_creacion
                    ot.tfs_minutos = int(duracion_total.total_seconds() / 60)
                    HistorialOT.objects.create(
                        orden_de_trabajo=ot, usuario=request.user, tipo_evento='FINALIZACION', 
                        descripcion=f"La OT ha sido finalizada. TFS registrado: {ot.tfs_minutos} min."
                    )
                
                ot.estado = nuevo_estado
                ot.save()
                
                messages.success(request, f"Estado de la OT actualizado a '{ot.get_estado_display()}'.")
                return redirect('ot_detail', pk=ot.pk)
            else:
                cambiar_estado_form = form
            
                # --- Lógica para Cerrar por Mecánico (CON NOTIFICACIÓN) ---
        elif 'cerrar_mecanico' in request.POST:
            form = CerrarOtMecanicoForm(request.POST, instance=ot)
            if form.is_valid():
                # Guardamos la OT primero
                instancia = form.save(commit=False)
                instancia.estado = 'CERRADA_MECANICO'
                instancia.save()

                # Creamos el registro en el historial
                HistorialOT.objects.create(
                    orden_de_trabajo=ot,
                    usuario=request.user,
                    tipo_evento='CIERRE_MECANICO',
                    descripcion=f"Cerrada por mecánico. Notas: {instancia.motivo_pendiente or 'N/A'}"
                )
                messages.info(request, f"OT #{ot.folio} marcada como 'Cerrada por Mecánico'.")

                # --- Lógica de Notificación ---
                try:
                    # Notificamos a TODOS los Supervisores y Administradores
                    destinatarios = User.objects.filter(
                        Q(groups__name='Supervisor') | Q(groups__name='Administrador')
                    ).distinct()
                    
                    if destinatarios.exists():
                        mensaje_notificacion = f"La OT #{instancia.folio} ({instancia.vehiculo.numero_interno}) está lista para su revisión."
                        url_notificacion = reverse('ot_detail', args=[ot.pk])
                        
                        notificaciones_a_crear = [
                            Notificacion(
                                usuario_destino=destinatario,
                                mensaje=mensaje_notificacion,
                                url_destino=url_notificacion
                            ) for destinatario in destinatarios
                        ]
                        
                        Notificacion.objects.bulk_create(notificaciones_a_crear)
                        messages.success(request, f"Se ha notificado a {destinatarios.count()} gestor(es) para su revisión.")
                
                except Exception as e:
                    messages.error(request, f"La OT fue cerrada, pero ocurrió un error al crear las notificaciones: {e}")

                return redirect('ot_list') # Redirigimos a la lista de OTs del mecánico
            else:
                cerrar_mecanico_form = form

    context = {
        'ot': ot,
        # Variables de permiso para la plantilla
        'es_mecanico': es_mecanico,
        'puede_gestionar_tareas_y_personal': puede_gestionar_tareas_y_personal,
        'puede_realizar_acciones_criticas': puede_realizar_acciones_criticas,
        
        # Formularios
        'asignar_form': asignar_form,
        'cerrar_mecanico_form': cerrar_mecanico_form,
        'cambiar_estado_form': cambiar_estado_form,
        'manual_insumo_form': manual_insumo_form,
        'pausar_form': pausar_form,
        'diagnostico_form': diagnostico_form,
        'asignar_tarea_form': asignar_tarea_form,
    }
    return render(request, 'flota/orden_trabajo_detail.html', context)


@login_required
def historial_vehiculo(request, pk):
    connection.set_tenant(request.tenant)
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    ordenes = OrdenDeTrabajo.objects.filter(vehiculo=vehiculo).order_by('-fecha_creacion')
    context = {'vehiculo': vehiculo, 'ordenes': ordenes}
    return render(request, 'flota/historial_vehiculo.html', context)


@login_required
def pizarra_programacion(request):
    connection.set_tenant(request.tenant)
    filtro_form = CalendarioFiltroForm(request.GET or None)
    
    form_creacion_ot = OrdenDeTrabajoForm() 

    context = {
        'filtro_form': filtro_form,
        'form_creacion_ot': form_creacion_ot,
    } 
    return render(request, 'flota/pizarra_programacion.html', context)

def _limpiar_descripcion_tarea(descripcion):
    """
    Función auxiliar para limpiar la descripción de una tarea.
    Elimina los estados comunes (PR, COR, OK, PENDIENTE) y otros artefactos.
    """
    if not isinstance(descripcion, str):
        return None

    # Elimina los indicadores de estado y lo que les sigue (ej: "PR OK", "COR PENDIENTE", etc.)
    # La expresión regular busca las palabras PR, COR, CO, OK, PENDIENTE al final de una frase.
    # Usaremos un método más simple y robusto: buscar por palabras clave y cortar la cadena.
    
    terminos_a_cortar = [' PR ', ' COR ', ' COK ', ' PENDIENTE', ' OK']
    descripcion_limpia = descripcion
    
    for termino in terminos_a_cortar:
        if termino in descripcion_limpia:
            # Corta la cadena justo antes del término
            descripcion_limpia = descripcion_limpia.split(termino)[0]

    # Elimina cualquier número al final que pueda ser un folio o código (ej: '... 1167')
    descripcion_limpia = re.sub(r'\s+\d+$', '', descripcion_limpia)
    
    # Elimina espacios en blanco extra al principio o al final
    descripcion_limpia = descripcion_limpia.strip()

    # Si la descripción es muy corta después de limpiar, la descartamos
    if len(descripcion_limpia) < 5:
        return None
        
    return descripcion_limpia


@login_required
def carga_masiva(request):
    connection.set_tenant(request.tenant)
    if request.method == 'POST':
        form = CargaMasivaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    if 'archivo_programa_mantenimiento' in request.FILES:
                        archivo_excel = request.FILES['archivo_programa_mantenimiento']
                        df = pd.read_excel(archivo_excel, header=1)
                        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('.', '').str.replace('(', '').str.replace(')', '')
                        
                        creados = 0
                        actualizados = 0

                        for index, row in df.iterrows():
                            if pd.isna(row['n°_int']):
                                continue

                            modelo_obj, _ = ModeloVehiculo.objects.get_or_create(
                                nombre=str(row['modelo']).strip(),
                                defaults={'marca': str(row['marca']).strip(), 'tipo': str(row['tipo_veh']).strip()}
                            )
                            norma_obj, _ = NormaEuro.objects.get_or_create(nombre=str(row['norma']).strip())

                            vehiculo_obj, created = Vehiculo.objects.update_or_create(
                                numero_interno=str(int(row['n°_int'])),
                                defaults={
                                    'patente': str(row['ppu']).strip() if pd.notna(row['ppu']) else None,
                                    'modelo': modelo_obj,
                                    'norma_euro': norma_obj,
                                    'chasis': str(row.get('chasis')).strip() if pd.notna(row.get('chasis')) else None,
                                    'motor': str(row.get('motor')).strip() if pd.notna(row.get('motor')) else None,
                                    'razon_social': str(row.get('razón__social')).strip() if pd.notna(row.get('razón__social')) else None,
                                    'kilometraje_actual': int(row['km_actual']) if pd.notna(row['km_actual']) else 0,
                                    'aplicacion': str(row.get('aplic')).strip() if pd.notna(row.get('aplic')) else None,
                                }
                            )
                            
                            if created:
                                creados += 1
                            else:
                                actualizados += 1
                        
                        messages.success(request, f"Carga de flota completada: {creados} vehículos nuevos creados y {actualizados} vehículos actualizados.")
                    
                    # Aquí puedes añadir las otras lógicas de carga que tenías
                    # if 'archivo_pautas' in request.FILES: ...

            except Exception as e:
                messages.error(request, f"Ocurrió un error crítico durante la carga: {e}")
            
            return redirect('carga_masiva')
    else:
        form = CargaMasivaForm()

    context = {'form': form}
    return render(request, 'flota/carga_masiva.html', context)
@login_required
def indicadores_dashboard(request):
    connection.set_tenant(request.tenant)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    if request.GET.get('start_date') and request.GET.get('end_date'):
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    bitacoras = BitacoraDiaria.objects.filter(fecha__range=[start_date, end_date])
    ots_en_periodo = OrdenDeTrabajo.objects.filter(fecha_creacion__date__range=[start_date, end_date])
    kpis_mensuales = bitacoras.annotate(month=TruncMonth('fecha')).values('month').annotate(total_horas_op=Sum('horas_operativas'), total_horas_mant_prog=Sum('horas_mantenimiento_prog'), total_horas_falla=Sum('horas_falla')).order_by('month')
    labels_mes, disponibilidad_data, confiabilidad_data, utilizacion_data = [], [], [], []
    for kpi in kpis_mensuales:
        mes_label = kpi['month'].strftime('%B %Y')
        labels_mes.append(mes_label)
        horas_calendario, horas_op, horas_falla, horas_mant_prog = 730, kpi['total_horas_op'] or 0, kpi['total_horas_falla'] or 0, kpi['total_horas_mant_prog'] or 0
        horas_disponibles = float(horas_calendario - horas_mant_prog - horas_falla)
        disponibilidad = (horas_disponibles / horas_calendario) * 100 if horas_calendario > 0 else 0
        confiabilidad = ((horas_calendario - float(horas_falla)) / horas_calendario) * 100 if horas_calendario > 0 else 0
        utilizacion = (float(horas_op) / horas_disponibles) * 100 if horas_disponibles > 0 else 0
        disponibilidad_data.append(round(disponibilidad, 2))
        confiabilidad_data.append(round(confiabilidad, 2))
        utilizacion_data.append(round(utilizacion, 2))
    total_preventivas = ots_en_periodo.filter(tipo='PREVENTIVA').count()
    total_correctivas = ots_en_periodo.filter(tipo='CORRECTIVA').count()
    preventivas_finalizadas = ots_en_periodo.filter(tipo='PREVENTIVA', estado='FINALIZADA').count()
    preventivas_pendientes = total_preventivas - preventivas_finalizadas
    correctivas_finalizadas = ots_en_periodo.filter(tipo='CORRECTIVA', estado='FINALIZADA').count()
    correctivas_pendientes = total_correctivas - correctivas_finalizadas
    context = {
        'start_date': start_date.strftime('%Y-%m-%d'), 'end_date': end_date.strftime('%Y-%m-%d'),
        'labels_mes': json.dumps(labels_mes), 'disponibilidad_data': json.dumps(disponibilidad_data),
        'confiabilidad_data': json.dumps(confiabilidad_data), 'utilizacion_data': json.dumps(utilizacion_data),
        'total_preventivas': total_preventivas, 'total_correctivas': total_correctivas,
        'preventivas_finalizadas': preventivas_finalizadas, 'preventivas_pendientes': preventivas_pendientes,
        'correctivas_finalizadas': correctivas_finalizadas, 'correctivas_pendientes': correctivas_pendientes,
    }
    return render(request, 'flota/indicadores_dashboard.html', context)


@login_required
def analisis_fallas(request):
    connection.set_tenant(request.tenant)
    end_date_str = request.GET.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
    fallas = OrdenDeTrabajo.objects.filter(tipo='CORRECTIVA', tipo_falla__isnull=False, tfs_minutos__gt=0, fecha_creacion__date__range=[start_date, end_date]).values('tipo_falla__descripcion', 'tipo_falla__causa', 'tipo_falla__criticidad').annotate(tfs_total_falla=Sum('tfs_minutos')).order_by('-tfs_total_falla')
    tfs_gran_total = sum(item['tfs_total_falla'] for item in fallas)
    frec_acumulada, data_pareto = 0, []
    for item in fallas:
        frec_relativa = (item['tfs_total_falla'] / tfs_gran_total) * 100 if tfs_gran_total > 0 else 0
        frec_acumulada += frec_relativa
        item['frecuencia_relativa'] = round(frec_relativa, 2)
        item['frecuencia_acumulada'] = round(frec_acumulada, 2)
        data_pareto.append(item)
    context = {
        'data_pareto_tabla': data_pareto, 'labels': json.dumps([item['tipo_falla__descripcion'] for item in data_pareto]),
        'frecuencia_data': json.dumps([item['frecuencia_relativa'] for item in data_pareto]), 'acumulada_data': json.dumps([item['frecuencia_acumulada'] for item in data_pareto]),
        'start_date': start_date.strftime('%Y-%m-%d'), 'end_date': end_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'flota/analisis_fallas.html', context)


@login_required
def analisis_avanzado(request):
    connection.set_tenant(request.tenant)
    proveedores = Proveedor.objects.all()
    tipos_vehiculo = ModeloVehiculo.objects.all()
    formatos = OrdenDeTrabajo.FORMATO_CHOICES
    ots = OrdenDeTrabajo.objects.filter(estado='FINALIZADA', costo_total__gt=0)
    proveedor_id = request.GET.get('proveedor')
    if proveedor_id: ots = ots.filter(proveedor_id=proveedor_id)
    formato_filtro = request.GET.get('formato')
    if formato_filtro: ots = ots.filter(formato=formato_filtro)
    tipo_veh_id = request.GET.get('tipo_vehiculo')
    if tipo_veh_id: ots = ots.filter(vehiculo__modelo_id=tipo_veh_id)
    tco_data = ots.values('proveedor__nombre').annotate(costo_sum=Sum('costo_total'), km_recorrido_sum=Sum(F('kilometraje_cierre') - F('kilometraje_apertura'))).order_by('-costo_sum')
    for item in tco_data:
        km_recorridos = item['km_recorrido_sum'] or 0
        item['costo_por_km'] = (item['costo_sum'] / km_recorridos) if km_recorridos > 0 else 0
        item['km_prom_mes'] = random.randint(3000, 5000)
    labels = [item['proveedor__nombre'] for item in tco_data]
    costo_total_data = [float(item['costo_sum']) for item in tco_data]
    costo_km_data = [float(item['costo_por_km']) for item in tco_data]
    km_mes_data = [item['km_prom_mes'] for item in tco_data]
    context = {
        'proveedores': proveedores, 'tipos_vehiculo': tipos_vehiculo, 'formatos': formatos, 'tco_data': tco_data,
        'labels': json.dumps(labels), 'costo_total_data': json.dumps(costo_total_data),
        'costo_km_data': json.dumps(costo_km_data), 'km_mes_data': json.dumps(km_mes_data),
        'selected_proveedor': int(proveedor_id) if proveedor_id else None,
        'selected_formato': formato_filtro,
        'selected_tipo_vehiculo': int(tipo_veh_id) if tipo_veh_id else None,
    }
    return render(request, 'flota/analisis_avanzado.html', context)


# --- Vistas de Acciones ---

@login_required
def cambiar_estado_ot(request, pk):
    connection.set_tenant(request.tenant)
    ot = get_object_or_404(OrdenDeTrabajo, pk=pk)
    if request.method == 'POST':
        form = CambiarEstadoOTForm(request.POST, instance=ot)
        if form.is_valid():
            form.save()
            messages.success(request, f"Estado de la OT #{ot.folio} actualizado a '{form.cleaned_data['estado']}'.")
    return redirect('ot_detail', pk=ot.pk)


@login_required
def generar_ot_pdf(request, pk):
    connection.set_tenant(request.tenant)
    ot = get_object_or_404(OrdenDeTrabajo, pk=pk)
    html_string = render_to_string('flota/ot_pdf_template.html', {'ot': ot, 'request': request})
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="OT-{ot.pk}.pdf"'
    return response

@login_required
def actualizar_km_vehiculo(request, pk):
    connection.set_tenant(request.tenant)
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    if request.method == 'POST':
        nuevo_km = request.POST.get('kilometraje_actual')
        if nuevo_km and nuevo_km.isdigit():
            vehiculo.kilometraje_actual = int(nuevo_km)
            vehiculo.save(update_fields=['kilometraje_actual'])
            messages.success(request, f"Kilometraje del vehículo {vehiculo.numero_interno} actualizado a {nuevo_km} KM.")
        else:
            messages.error(request, "El kilometraje ingresado no es válido.")
    return redirect('dashboard')

@login_required
def analisis_km_vehiculo(request, pk):
    """
    Vista para mostrar el análisis de kilometraje y calcular pronósticos
    para un vehículo específico.
    """
    connection.set_tenant(request.tenant)
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    
    km_actual = vehiculo.kilometraje_actual
    proxima_pauta_agg = PautaMantenimiento.objects.filter(
        modelo_vehiculo=vehiculo.modelo,
        kilometraje_pauta__gt=km_actual
    ).aggregate(proximo_km=Min('kilometraje_pauta'))
    proximo_km_pauta = proxima_pauta_agg.get('proximo_km')

    kms_faltantes = None
    if proximo_km_pauta:
        kms_faltantes = proximo_km_pauta - km_actual
    
    km_prom_dia_actual = random.randint(150, 450)
    
    fecha_pronosticada = None
    km_prom_usado = km_prom_dia_actual 

    if request.method == 'POST':
        km_prom_input = request.POST.get('km_prom_diario')
        if km_prom_input and km_prom_input.isdigit():
            km_prom_usado = int(km_prom_input)

    if kms_faltantes is not None and kms_faltantes > 0 and km_prom_usado > 0:
        dias_para_pauta = kms_faltantes / km_prom_usado
        fecha_pronosticada = (datetime.now().date() + timedelta(days=dias_para_pauta)).strftime("%d de %B de %Y")

    context = {
        'vehiculo': vehiculo,
        'km_prom_dia_actual': km_prom_dia_actual,
        'proximo_km_pauta': proximo_km_pauta,
        'kms_faltantes': kms_faltantes,
        'fecha_pronosticada': fecha_pronosticada,
        'km_prom_usado': km_prom_usado, 
    }
    
    return render(request, 'flota/analisis_km.html', context)

@login_required
def eliminar_tarea_ot(request, ot_pk, tarea_pk):
    connection.set_tenant(request.tenant)
    ot = get_object_or_404(OrdenDeTrabajo, pk=ot_pk)
    tarea = get_object_or_404(Tarea, pk=tarea_pk)
    if request.method == 'POST':
        ot.tareas_realizadas.remove(tarea)
        ot.save() 
        messages.warning(request, f'Tarea "{tarea.descripcion}" eliminada de la OT.')
    return redirect('ot_detail', pk=ot_pk)

@login_required
def eliminar_insumo_ot(request, ot_pk, detalle_pk):
    connection.set_tenant(request.tenant)
    ot = get_object_or_404(OrdenDeTrabajo, pk=ot_pk)
    detalle = get_object_or_404(DetalleInsumoOT, pk=detalle_pk)
    
    if request.method == 'POST':
        # Determinar el nombre del insumo/repuesto para el mensaje
        if detalle.repuesto_inventario:
            item_nombre = f"{detalle.repuesto_inventario.nombre} ({detalle.repuesto_inventario.numero_parte})"
        elif detalle.insumo:
            item_nombre = detalle.insumo.nombre
        else:
            item_nombre = "Insumo Desconocido" # En caso de que ambos sean None (aunque el CheckConstraint lo previene)

        with transaction.atomic(): 
            if detalle.repuesto_inventario:
                MovimientoStock.objects.create(
                    repuesto=detalle.repuesto_inventario,
                    tipo_movimiento='AJUSTE_POSITIVO', # O 'ENTRADA' si prefieres esa clasificación
                    cantidad=detalle.cantidad, # Cantidad positiva para devolver al stock
                    usuario_responsable=request.user,
                    orden_de_trabajo=ot, # Asociar al OT para trazabilidad
                    notas=f"Devolución de stock por eliminación de insumo '{item_nombre}' de OT #{ot.folio}"
                )

            detalle.delete()
            ot.save() # Para recalcular costos
            messages.warning(request, f'"{item_nombre}" eliminado de la OT. Stock devuelto al inventario si aplica.')
            
    return redirect('ot_detail', pk=ot_pk)

@login_required
def mecanicos_recursos_api(request):
    """
    API que devuelve una lista de usuarios que son Mecánicos o Supervisores
    en el formato que FullCalendar Resource-Timeline necesita.
    """
    connection.set_tenant(request.tenant)
    recursos_qs = User.objects.filter(groups__name__in=['Mecánico', 'Supervisor']).distinct()
    recursos = []
    for usuario in recursos_qs:
        recursos.append({
            'id': usuario.pk,
            'title': usuario.get_full_name() or usuario.username,
        })
    return JsonResponse(recursos, safe=False)

@login_required
def actualizar_fecha_ot_api(request, pk):
    """
    API para actualizar la fecha_programada de una OT cuando se arrastra
    en el calendario.
    """
    connection.set_tenant(request.tenant)
    if request.method == 'POST':
        try:
            ot = OrdenDeTrabajo.objects.get(pk=pk)
            data = json.loads(request.body)
            nueva_fecha_str = data.get('fecha_programada')

            if nueva_fecha_str:
                ot.fecha_programada = datetime.fromisoformat(nueva_fecha_str.split('T')[0]).date()
                ot.save(update_fields=['fecha_programada'])
                
                HistorialOT.objects.create(
                    orden_de_trabajo=ot, usuario=request.user, tipo_evento='MODIFICACION',
                    descripcion=f"OT reprogramada para el {ot.fecha_programada.strftime('%d/%m/%Y')}."
                )
                return JsonResponse({'status': 'ok', 'message': 'Fecha actualizada con éxito.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'No se proporcionó una nueva fecha.'}, status=400)
        except OrdenDeTrabajo.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'OT no encontrada.'}, status=404)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return JsonResponse({'status': 'error', 'message': f'Datos inválidos: {e}'}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

@login_required
def repuesto_list(request):
    """
    Vista para listar todos los repuestos en el inventario (la "Pizarra de Repuestos").
    Incluye una funcionalidad de búsqueda simple.
    """
    connection.set_tenant(request.tenant)
    query = request.GET.get('q', '')
    if query:
        repuestos = Repuesto.objects.filter(
            Q(nombre__icontains=query) | Q(numero_parte__icontains=query)
        ).order_by('nombre')
    else:
        repuestos = Repuesto.objects.all().order_by('nombre')
    
    context = {
        'repuestos': repuestos,
        'query': query,
    }
    return render(request, 'flota/repuesto_list.html', context)


@login_required
def repuesto_create(request):
    """
    Vista para crear un nuevo repuesto.
    """
    connection.set_tenant(request.tenant)
    if request.method == 'POST':
        form = RepuestoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Repuesto creado con éxito.')
            return redirect('repuesto_list')
        else:
            # SI EL FORMULARIO NO ES VÁLIDO, AHORA MANEJAMOS LOS ERRORES
            messages.error(request, 'Error al crear el repuesto. Por favor, corrija los errores.')
            # Recorre los errores del formulario y los añade a los mensajes para el usuario
            for field, errors in form.errors.items():
                for error in errors:
                    # Intenta obtener el label del campo, si no existe usa el nombre del campo capitalizado
                    label = form.fields[field].label if field in form.fields else field.capitalize()
                    messages.error(request, f"Error en '{label}': {error}")
            # NO HACEMOS REDIRECCIÓN AQUÍ para que el formulario se re-renderice con los errores
            # El código caerá al final de la función para renderizar la plantilla con el 'form' que contiene los errores.
    else: # Si el método es GET, inicializamos un formulario vacío
        form = RepuestoForm()
    
    context = {
        'form': form # El formulario se pasa al contexto, ya sea vacío o con errores
    }
    return render(request, 'flota/repuesto_form.html', context)


@login_required
def repuesto_update(request, pk):
    """
    Vista para actualizar un repuesto existente.
    """
    connection.set_tenant(request.tenant)
    repuesto = get_object_or_404(Repuesto, pk=pk)
    if request.method == 'POST':
        form = RepuestoForm(request.POST, instance=repuesto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Repuesto actualizado con éxito.')
            return redirect('repuesto_list')
    else:
        form = RepuestoForm(instance=repuesto)
        
    context = {
        'form': form,
        'repuesto': repuesto
    }
    return render(request, 'flota/repuesto_form.html', context)

@login_required
def registrar_movimiento(request, repuesto_pk):
    """
    Vista para registrar una entrada, salida o ajuste manual de stock
    para un repuesto específico.
    """
    connection.set_tenant(request.tenant)
    repuesto = get_object_or_404(Repuesto, pk=repuesto_pk)
    
    if request.method == 'POST':
        form = MovimientoStockForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.repuesto = repuesto
            movimiento.usuario_responsable = request.user
            
            movimiento.save() 
            
            messages.success(request, f'Movimiento de stock para "{repuesto.nombre}" registrado con éxito.')
            return redirect('repuesto_detail', pk=repuesto.pk) 
    else:
        form = MovimientoStockForm()
        
    context = {
        'form': form,
        'repuesto': repuesto
    }
    return render(request, 'flota/movimiento_stock_form.html', context)


@login_required
def repuesto_detail(request, pk):
    """
    Vista para ver el detalle y el historial de movimientos de un repuesto.
    """
    connection.set_tenant(request.tenant)
    repuesto = get_object_or_404(Repuesto, pk=pk)
    movimientos = repuesto.movimientos.all() 
    
    context = {
        'repuesto': repuesto,
        'movimientos': movimientos,
    }
    return render(request, 'flota/repuesto_detail.html', context)

@login_required
def repuesto_search_api(request):
    """
    API que busca repuestos por nombre o número de parte y los devuelve en JSON.
    """
    connection.set_tenant(request.tenant)
    query = request.GET.get('q', '')
    
    if len(query) < 2: 
        return JsonResponse([], safe=False)
        
    repuestos = Repuesto.objects.filter(
        Q(nombre__icontains=query) | Q(numero_parte__icontains=query)
    )[:10] 
    
    results = []
    for repuesto in repuestos:
        results.append({
            'id': repuesto.id,
            'text': f"{repuesto.nombre} ({repuesto.numero_parte})",
            'stock': repuesto.stock_actual,
            'calidad': repuesto.get_calidad_display(),
        })
        
    return JsonResponse(results, safe=False)

@login_required
def add_repuesto_a_ot_api(request):
    """
    API para añadir un repuesto a una OT y descontar el stock.
    Espera una petición POST con JSON.
    """
    connection.set_tenant(request.tenant)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        ot_id = int(data.get('ot_id'))
        repuesto_id = int(data.get('repuesto_id'))
        cantidad = int(data.get('cantidad'))

        if cantidad <= 0:
            return JsonResponse({'status': 'error', 'message': 'La cantidad debe ser mayor que cero.'}, status=400)

        with transaction.atomic():
            ot = get_object_or_404(OrdenDeTrabajo, pk=ot_id)
            repuesto = get_object_or_404(Repuesto, pk=repuesto_id)

            if repuesto.stock_actual < cantidad:
                return JsonResponse({'status': 'error', 'message': f'Stock insuficiente. Stock actual: {repuesto.stock_actual}'}, status=400)

            # Verificar si ya existe un DetalleInsumoOT para este repuesto_inventario en esta OT.
            # Si existe, actualizamos la cantidad en lugar de crear una nueva entrada.
            detalle_existente = DetalleInsumoOT.objects.filter(
                orden_de_trabajo=ot, repuesto_inventario=repuesto
            ).first()

            if detalle_existente:
                detalle_existente.cantidad += cantidad
                detalle_existente.save()
                messages_info = f'Cantidad de "{repuesto.nombre}" actualizada en la OT. Total: {detalle_existente.cantidad}.'
            else:
                # Crear un nuevo DetalleInsumoOT vinculando directamente al Repuesto del inventario
                DetalleInsumoOT.objects.create(
                    orden_de_trabajo=ot,
                    repuesto_inventario=repuesto, # <--- ¡Este es el cambio clave!
                    insumo=None, # Asegúrate de que el campo 'insumo' quede vacío para los de inventario
                    cantidad=cantidad
                )
                messages_info = f'Repuesto "{repuesto.nombre}" añadido a la OT con éxito.'

            # Descontar el stock y registrar el movimiento de stock.
            MovimientoStock.objects.create(
                repuesto=repuesto,
                tipo_movimiento='SALIDA_OT',
                cantidad=-cantidad, 
                usuario_responsable=request.user,
                orden_de_trabajo=ot,
                notas=f"Salida automática para OT #{ot.folio}"
            )
            
            # Recalcular el costo total de la OT después de añadir el insumo
            ot.save()
        
        return JsonResponse({'status': 'ok', 'message': messages_info})

    except KeyError:
        return JsonResponse({'status': 'error', 'message': 'Faltan datos en la petición (ot_id, repuesto_id, cantidad).'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Los IDs y la cantidad deben ser números enteros.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON mal formado en el cuerpo de la petición.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ha ocurrido un error inesperado en el servidor: {e}'}, status=500)
    


def predecir_consumo_para_ruta(vehiculo, ruta, distancia_personalizada=None):
    if distancia_personalizada:
        try:
            distancia_a_recorrer = float(distancia_personalizada)
        except (ValueError, TypeError):
            return {'error': 'La distancia personalizada debe ser un número válido.'}
    else:
        distancia_a_recorrer = float(ruta.distancia_km)

    rendimiento_en_ruta = CargaCombustible.objects.filter(
        vehiculo=vehiculo, ruta=ruta, rendimiento_calculado_kml__isnull=False
    ).aggregate(promedio=Avg('rendimiento_calculado_kml'))['promedio']

    if not rendimiento_en_ruta:
        rendimiento_general = CargaCombustible.objects.filter(
            vehiculo=vehiculo, rendimiento_calculado_kml__isnull=False
        ).aggregate(promedio=Avg('rendimiento_calculado_kml'))['promedio']
        if not rendimiento_general:
            return {'error': 'No hay suficientes datos de rendimiento para este vehículo.'}
        rendimiento_base = float(rendimiento_general)
        fuente_rendimiento = "promedio general del vehículo"
    else:
        rendimiento_base = float(rendimiento_en_ruta)
        fuente_rendimiento = f"histórico en la ruta '{ruta.nombre}'"

    rendimiento_ajustado = rendimiento_base
    if rendimiento_ajustado <= 0:
        return {'error': 'El rendimiento calculado es cero o negativo, no se puede predecir.'}
        
    consumo_predicho_litros = distancia_a_recorrer / rendimiento_ajustado

    return {
        'error': None, 'vehiculo': vehiculo, 'ruta': ruta, 'distancia_utilizada': distancia_a_recorrer,
        'rendimiento_base_kml': rendimiento_base, 'fuente_del_rendimiento': fuente_rendimiento,
        'consumo_predicho_litros': consumo_predicho_litros
    }

@login_required
def registrar_carga_combustible(request):
    connection.set_tenant(request.tenant)
    if request.method == 'POST':
        form = CargaCombustibleForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                condicion, created = CondicionAmbiental.objects.get_or_create(
                    fecha_medicion=form.cleaned_data['fecha_carga'].date(),
                    defaults={
                        'temperatura_celsius': form.cleaned_data['temperatura_celsius'],
                        'condicion_climatica': form.cleaned_data['condicion_climatica'],
                        'nivel_trafico': form.cleaned_data['nivel_trafico'],
                    }
                )
                nueva_carga = form.save(commit=False)
                nueva_carga.condicion_ambiental = condicion
                nueva_carga.save()
            messages.success(request, f"Carga de combustible para {nueva_carga.vehiculo.numero_interno} registrada con éxito.")
            return redirect('pizarra_combustible')
        else:
            messages.error(request, "Error al registrar la carga. Por favor, corrija los errores.")
    else:
        form = CargaCombustibleForm()

    context = {
        'form': form,
    }
    return render(request, 'flota/registrar_carga_combustible.html', context)


# Reemplaza la función pizarra_combustible completa en flota/views.py

@login_required
def pizarra_combustible(request):
    connection.set_tenant(request.tenant)
    form = CargaCombustibleForm()
    resultado_prediccion = None
    vehiculo_seleccionado = None
    analisis_vehiculo_seleccionado = None

    # --- Lógica de Procesamiento de Formularios POST (sin cambios) ---
    if request.method == 'POST':
        if 'registrar_carga' in request.POST:
            # ... (tu lógica de registro)
            pass
        elif 'predecir_consumo' in request.POST:
            # ... (tu lógica de predicción)
            pass

    # --- Lógica para mostrar los datos (GET) ---
    todos_los_vehiculos = Vehiculo.objects.select_related('modelo').order_by('numero_interno') # Optimizamos la consulta
    vehiculo_id_seleccionado = request.GET.get('vehiculo_id')
    
    if vehiculo_id_seleccionado:
        try:
            vehiculo_seleccionado = get_object_or_404(Vehiculo, pk=vehiculo_id_seleccionado)
            
            # Análisis del vehículo
            rendimiento_general = CargaCombustible.objects.filter(
                vehiculo=vehiculo_seleccionado, rendimiento_calculado_kml__isnull=False
            ).aggregate(promedio=Avg('rendimiento_calculado_kml'))['promedio']
            
            # === INICIO DE LA NUEVA LÓGICA DEL SEMÁFORO ===
            estado_rendimiento = "SIN_DATOS"
            if rendimiento_general is not None:
                # Accedemos a los umbrales del modelo del vehículo
                modelo = vehiculo_seleccionado.modelo
                if rendimiento_general >= modelo.rendimiento_optimo_kml:
                    estado_rendimiento = "OPTIMO"
                elif rendimiento_general >= modelo.rendimiento_regular_kml:
                    estado_rendimiento = "REGULAR"
                else:
                    estado_rendimiento = "DEFICIENTE"
            # === FIN DE LA NUEVA LÓGICA DEL SEMÁFORO ===

            # Análisis por ruta y conductor (sin cambios)
            rendimiento_por_ruta = CargaCombustible.objects.filter(vehiculo=vehiculo_seleccionado, rendimiento_calculado_kml__isnull=False).values('ruta__nombre').annotate(promedio_ruta=Avg('rendimiento_calculado_kml')).order_by('-promedio_ruta')
            rendimiento_por_conductor = CargaCombustible.objects.filter(vehiculo=vehiculo_seleccionado, rendimiento_calculado_kml__isnull=False).values('conductor__username').annotate(promedio_conductor=Avg('rendimiento_calculado_kml')).order_by('-promedio_conductor')
            historial_cargas = CargaCombustible.objects.filter(vehiculo=vehiculo_seleccionado)

            # Empaquetamos todo en el diccionario de análisis
            analisis_vehiculo_seleccionado = {
                'vehiculo': vehiculo_seleccionado,
                'rendimiento_general': rendimiento_general,
                'estado_rendimiento': estado_rendimiento, # <-- Pasamos el nuevo estado
                'analisis_por_ruta': list(rendimiento_por_ruta),
                'analisis_por_conductor': list(rendimiento_por_conductor),
                'historial_cargas': historial_cargas,
            }
        except (ValueError, TypeError):
            messages.error(request, "El ID del vehículo seleccionado no es válido.")

    context = {
        'form': form,
        'todos_los_vehiculos': todos_los_vehiculos,
        'vehiculo_seleccionado': vehiculo_seleccionado,
        'analisis': analisis_vehiculo_seleccionado,
        'resultado_prediccion': resultado_prediccion,
    }
    return render(request, 'flota/pizarra_combustible.html', context)


@login_required
@user_passes_test(es_supervisor_o_admin)
def autorizar_horas_extra(request, pk):
    connection.set_tenant(request.tenant)
    ot = get_object_or_404(OrdenDeTrabajo, pk=pk)

    if request.method == 'POST':
        ot.horas_extra_autorizadas = True
        
        if ot.estado == 'PAUSADA':
            ot.estado = 'EN_PROCESO'
            
        ot.save()

        HistorialOT.objects.create(
            orden_de_trabajo=ot,
            usuario=request.user,
            tipo_evento='MODIFICACION',
            descripcion="Se han autorizado las horas extra para esta OT."
        )

        messages.success(request, f"¡Horas extra autorizadas para la OT #{ot.folio}!")
    
    return redirect('ot_detail', pk=pk)

@login_required
def lista_notificaciones(request):
    """
    Muestra todas las notificaciones del usuario, paginadas.
    """
    connection.set_tenant(request.tenant)
    
    # Obtenemos todas las notificaciones del usuario logueado
    notificaciones_list = request.user.notificaciones.all()
    
    # Paginación
    paginator = Paginator(notificaciones_list, 20) # Muestra 20 notificaciones por página
    page = request.GET.get('page')
    try:
        notificaciones = paginator.page(page)
    except PageNotAnInteger:
        notificaciones = paginator.page(1)
    except EmptyPage:
        notificaciones = paginator.page(paginator.num_pages)
        
    context = {
        'notificaciones': notificaciones
    }
    return render(request, 'flota/lista_notificaciones.html', context)

@login_required
def marcar_notificaciones_leidas(request):
    """
    API view que marca todas las notificaciones no leídas del usuario como leídas.
    Se llama vía JavaScript (fetch).
    """
    if request.method == 'POST':
        # Buscamos todas las notificaciones NO leídas del usuario y las actualizamos
        request.user.notificaciones.filter(leida=False).update(leida=True)
        return JsonResponse({'status': 'ok'})
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
@user_passes_test(es_supervisor_o_admin) # Solo supervisores y admins pueden ver la lista
def lista_usuarios(request):
    """
    Muestra una lista de todos los usuarios del tenant actual.
    """
    connection.set_tenant(request.tenant)
    
    # Obtenemos todos los usuarios, excepto el superusuario si existiera en este tenant (poco probable pero seguro)
    # y los ordenamos por nombre de usuario.
    usuarios = User.objects.filter(is_superuser=False).order_by('username')
    
    context = {
        'usuarios': usuarios
    }
    return render(request, 'flota/administracion/lista_usuarios.html', context)


@login_required
@user_passes_test(es_supervisor_o_admin) # Solo supervisores y admins pueden crear usuarios
def crear_usuario(request):
    """
    Gestiona la creación de un nuevo usuario y su asignación a un grupo (rol).
    """
    connection.set_tenant(request.tenant)
    
    if request.method == 'POST':
        form = UsuarioCreacionForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Obtenemos los datos limpios del formulario
                    username = form.cleaned_data['username']
                    password = form.cleaned_data['password']
                    email = form.cleaned_data['email']
                    first_name = form.cleaned_data['first_name']
                    last_name = form.cleaned_data['last_name']
                    grupo = form.cleaned_data['grupo']

                    # Creamos el nuevo usuario
                    nuevo_usuario = User.objects.create_user(
                        username=username,
                        password=password,
                        email=email,
                        first_name=first_name,
                        last_name=last_name
                    )

                    # Asignamos el usuario al grupo seleccionado
                    nuevo_usuario.groups.add(grupo)

                    messages.success(request, f'Usuario "{username}" creado y asignado al rol "{grupo.name}" con éxito.')
                    return redirect('lista_usuarios')
            
            except Exception as e:
                messages.error(request, f'Ocurrió un error al crear el usuario: {e}')
                
    else: # Si es una petición GET
        form = UsuarioCreacionForm()

    context = {
        'form': form
    }
    return render(request, 'flota/administracion/crear_usuario.html', context)


@login_required
@user_passes_test(es_supervisor_o_admin) # Solo supervisores y admins pueden editar
def editar_usuario(request, user_id):
    """
    Gestiona la edición de los datos y el rol de un usuario existente.
    """
    connection.set_tenant(request.tenant)
    usuario_a_editar = get_object_or_404(User, pk=user_id, is_superuser=False)

    if request.method == 'POST':
        form = UsuarioEdicionForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Actualizamos los datos del usuario
                    usuario_a_editar.first_name = form.cleaned_data['first_name']
                    usuario_a_editar.last_name = form.cleaned_data['last_name']
                    usuario_a_editar.email = form.cleaned_data['email']
                    usuario_a_editar.save()

                    # Actualizamos el grupo (rol)
                    grupo_nuevo = form.cleaned_data['grupo']
                    usuario_a_editar.groups.clear() # Quitamos todos los grupos anteriores
                    usuario_a_editar.groups.add(grupo_nuevo) # Añadimos el nuevo grupo

                    messages.success(request, f'Usuario "{usuario_a_editar.username}" actualizado con éxito.')
                    return redirect('lista_usuarios')
            
            except Exception as e:
                messages.error(request, f'Ocurrió un error al editar el usuario: {e}')

    else: # Si es una petición GET
        # Pre-poblamos el formulario con los datos actuales del usuario
        initial_data = {
            'first_name': usuario_a_editar.first_name,
            'last_name': usuario_a_editar.last_name,
            'email': usuario_a_editar.email,
            'grupo': usuario_a_editar.groups.first(), # Obtenemos el primer (y único) grupo del usuario
        }
        form = UsuarioEdicionForm(initial=initial_data)

    context = {
        'form': form,
        'usuario_a_editar': usuario_a_editar
    }
    return render(request, 'flota/administracion/editar_usuario.html', context)

@login_required
@user_passes_test(lambda u: es_administrador(u) or es_gerente(u))
def kpi_rrhh_dashboard(request):
    """
    Dashboard para mostrar los KPIs de Recursos Humanos.
    """
    connection.set_tenant(request.tenant)

    # --- Lógica de Filtro de Fechas ---
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    if request.GET.get('start_date') and request.GET.get('end_date'):
        try:
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')
            start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass

    # --- Cálculos para el período seleccionado ---
    ots_finalizadas_periodo = OrdenDeTrabajo.objects.filter(estado='FINALIZADA', fecha_cierre__date__range=[start_date, end_date])

    # KPI 1: Productividad (lógica existente)
    minutos_estandar_totales = ots_finalizadas_periodo.aggregate(total=Sum('tareas_realizadas__tiempo_estandar_minutos'))['total'] or 0
    minutos_reales_trabajados = ots_finalizadas_periodo.aggregate(total=Sum('tfs_minutos'))['total'] or 0
    kpi_productividad = (minutos_estandar_totales / minutos_reales_trabajados) * 100 if minutos_reales_trabajados > 0 else 0

    # KPI 2: Cumplimiento (lógica existente)
    ots_programadas_en_periodo = OrdenDeTrabajo.objects.filter(fecha_programada__range=[start_date, end_date])
    total_programadas = ots_programadas_en_periodo.count()
    finalizadas_a_tiempo = ots_programadas_en_periodo.filter(estado='FINALIZADA', fecha_cierre__date__lte=F('fecha_programada')).count()
    kpi_cumplimiento = (finalizadas_a_tiempo / total_programadas) * 100 if total_programadas > 0 else 0

    # === INICIO DE LA NUEVA LÓGICA PARA EL KPI 3 ===
    # KPI 3: Utilización de Recursos

    # 1. Obtener los parámetros de configuración
    config = ConfiguracionEmpresa.load()
    horas_mes_persona = config.horas_laborales_mes_por_persona

    # 2. Contar el número de técnicos activos
    numero_de_tecnicos = User.objects.filter(groups__name='Mecánico', is_active=True).count()

    # 3. Calcular los minutos disponibles totales del equipo para el período
    #    (Es una aproximación. Una versión más avanzada calcularía los días laborables exactos)
    num_dias_periodo = (end_date - start_date).days + 1
    # Asumimos un mes de ~30.4 días para la proporción
    proporcion_mes = num_dias_periodo / 30.4
    minutos_disponibles_totales = (numero_de_tecnicos * horas_mes_persona * 60) * proporcion_mes

    # 4. Calcular el KPI de Utilización
    kpi_utilizacion = (minutos_reales_trabajados / minutos_disponibles_totales) * 100 if minutos_disponibles_totales > 0 else 0
    # === FIN DE LA NUEVA LÓGICA ===
    
    # --- Datos para Gráficos (sin cambios por ahora) ---
    # ... tu lógica de gráficos existente ...
    
    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        
        # KPI 1
        'kpi_productividad': kpi_productividad,
        # KPI 2
        'kpi_cumplimiento': kpi_cumplimiento,
        
        # KPI 3 (nuevos datos)
        'numero_de_tecnicos': numero_de_tecnicos,
        'minutos_disponibles_totales': minutos_disponibles_totales,
        'minutos_reales_trabajados': minutos_reales_trabajados, # Ya lo teníamos, pero lo pasamos de nuevo para esta tarjeta
        'kpi_utilizacion': kpi_utilizacion,

        # ... tus otros datos de contexto para tarjetas y gráficos ...
    }

    return render(request, 'flota/kpi_rrhh_dashboard.html', context)

@login_required
@user_passes_test(lambda u: es_administrador(u) or es_gerente(u))
def reportes_dashboard(request):
    """
    Página principal para la generación de reportes.
    Inicialmente, permite exportar OTs a CSV.
    """
    connection.set_tenant(request.tenant)

    # Lógica para manejar la petición de exportación
    if request.method == 'POST':
        # Obtenemos las fechas del formulario
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        try:
            start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError, AttributeError):
            messages.error(request, "Formato de fecha inválido. Por favor, seleccione un rango de fechas.")
            return redirect('reportes_dashboard')

        # Filtramos las OTs en el rango de fechas de CIERRE
        ordenes = OrdenDeTrabajo.objects.filter(
            fecha_cierre__date__range=[start_date, end_date]
        ).select_related(
            'vehiculo', 'vehiculo__modelo', 'responsable', 'tipo_falla'
        ).prefetch_related('tareas_realizadas', 'detalles_insumos_ot')
        
        if not ordenes.exists():
            messages.warning(request, "No se encontraron Órdenes de Trabajo en el período seleccionado para exportar.")
            return redirect('reportes_dashboard')

        # --- Lógica de Generación de CSV ---
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="reporte_ots_{start_date_str}_a_{end_date_str}.csv"'},
        )
        response.write(u'\ufeff'.encode('utf8')) # BOM para que Excel reconozca UTF-8

        writer = csv.writer(response, delimiter=';') # Usamos punto y coma como delimitador, común en Excel en español
        
        # Escribimos la cabecera del CSV
        writer.writerow([
            'Folio OT', 'Estado', 'Tipo', 'Vehiculo Numero', 'Vehiculo Patente', 
            'Fecha Creacion', 'Fecha Cierre', 'Kilometraje Apertura', 'Kilometraje Cierre',
            'Responsable', 'Costo Total', 'TFS (Minutos)', 'Tipo de Falla', 'Tareas'
        ])

        # Escribimos los datos de cada OT
        for ot in ordenes:
            # Concatenamos las descripciones de las tareas
            tareas_str = ", ".join([tarea.descripcion for tarea in ot.tareas_realizadas.all()])
            
            writer.writerow([
                ot.folio,
                ot.get_estado_display(),
                ot.get_tipo_display(),
                ot.vehiculo.numero_interno,
                ot.vehiculo.patente,
                ot.fecha_creacion.strftime('%d-%m-%Y %H:%M') if ot.fecha_creacion else '',
                ot.fecha_cierre.strftime('%d-%m-%Y %H:%M') if ot.fecha_cierre else '',
                ot.kilometraje_apertura,
                ot.kilometraje_cierre,
                ot.responsable.username if ot.responsable else 'N/A',
                f"{ot.costo_total:.2f}".replace('.',','), # Formato decimal para Excel en español
                ot.tfs_minutos,
                ot.tipo_falla.descripcion if ot.tipo_falla else 'N/A',
                tareas_str
            ])
        
        return response

    # Lógica para mostrar la página si la petición es GET
    context = {}
    return render(request, 'flota/reportes_dashboard.html', context)