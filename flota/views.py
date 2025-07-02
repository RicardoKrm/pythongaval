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

from .models import (
    Vehiculo, PautaMantenimiento, OrdenDeTrabajo, BitacoraDiaria, ModeloVehiculo,
    Tarea, Insumo, TipoFalla, Proveedor, DetalleInsumoOT, HistorialOT, Repuesto,
    MovimientoStock, RepuestoRequeridoPorTarea 
)
from .forms import (
    OrdenDeTrabajoForm, CambiarEstadoOTForm, BitacoraDiariaForm, CargaMasivaForm, 
    CerrarOtMecanicoForm, AsignarPersonalOTForm, ManualTareaForm, ManualInsumoForm, FiltroPizarraForm, AsignarTareaForm,
    PausarOTForm, DiagnosticoEvaluacionForm, OTFiltroForm, CalendarioFiltroForm, RepuestoForm, MovimientoStockForm

)
from django.utils import timezone 


# --- Función de chequeo de rol ---
def es_supervisor_o_admin(user):
    return user.groups.filter(name__in=['Supervisor', 'Administrador']).exists()


# --- Vistas Principales de la Aplicación ---

@login_required
def dashboard_flota(request):
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
    
    if request.method == 'POST':
        form = OrdenDeTrabajoForm(request.POST)
        if form.is_valid():
            ot = form.save()
            HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='CREACION', descripcion=f"OT #{ot.folio} creada con éxito.")
            messages.success(request, f'Orden de Trabajo #{ot.folio} creada con éxito.')
            if 'from_calendar' in request.GET:
                return redirect('pizarra_programacion')
            return redirect('ot_list')
        else:
            messages.error(request, 'Por favor, corrija los errores en el formulario.')
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label or field.capitalize()
                    messages.error(request, f"Error en '{label}': {error}")
            return redirect('ot_list')

    else:
        initial_data = {}
        
        vehiculo_id = request.GET.get('vehiculo_id')
        if vehiculo_id:
            initial_data['vehiculo'] = vehiculo_id
            initial_data['tipo'] = 'CORRECTIVA'
        
        fecha_programada_str = request.GET.get('fecha_programada')
        if fecha_programada_str:
            try:
                initial_data['fecha_programada'] = datetime.strptime(fecha_programada_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        form = OrdenDeTrabajoForm(initial=initial_data)

    ordenes_list = OrdenDeTrabajo.objects.all().select_related('vehiculo').order_by('-fecha_creacion')
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

    paginator = Paginator(ordenes_list, 10)
    page = request.GET.get('page')
    try:
        ordenes_paginadas = paginator.page(page)
    except PageNotAnInteger:
        ordenes_paginadas = paginator.page(1)
    except EmptyPage:
        ordenes_paginadas = paginator.page(paginator.num_pages)
    
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
    
    # Pre-fetch detalles_insumos_ot y repuesto_inventario para evitar consultas N+1
    # Asegúrate de que prefetch_related apunte a 'tareas_realizadas__repuestos_requeridos__repuesto'
    # para la lógica de disponibilidad, y a 'detalles_insumos_ot__repuesto_inventario'
    # si quieres acceder a los repuestos consumidos.
    ordenes_qs = OrdenDeTrabajo.objects.all().select_related('vehiculo', 'responsable').prefetch_related('tareas_realizadas__repuestos_requeridos__repuesto')
    
    # Lógica de filtros
    vehiculo_id = request.GET.get('vehiculo')
    estado = request.GET.get('estado')
    responsable_id = request.GET.get('responsable')
    # NUEVO: Filtro por disponibilidad de repuestos
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
            'title': f"OT-{ot.folio or ot.pk} ({ot.vehiculo.numero_interno})",
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
                'vehiculo_patente': ot.vehiculo.patente,
                'hasAllPartsAvailable': ot.has_all_parts_available(), # <-- ¡NUEVO CAMPO EN LA API!
            }
        })
            
    return JsonResponse(eventos, safe=False)

@login_required
def orden_trabajo_detail(request, pk):
    connection.set_tenant(request.tenant)
    ot = get_object_or_404(OrdenDeTrabajo, pk=pk)
    es_admin_o_super = request.user.groups.filter(name__in=['Administrador', 'Supervisor']).exists()
    
    # Inicialización de todos los formularios
    asignar_form = AsignarPersonalOTForm(instance=ot)
    cerrar_mecanico_form = CerrarOtMecanicoForm(instance=ot)
    cambiar_estado_form = CambiarEstadoOTForm(instance=ot)
    manual_tarea_form = ManualTareaForm() # Lo mantenemos por si acaso, pero será reemplazado en la plantilla
    manual_insumo_form = ManualInsumoForm()
    pausar_form = PausarOTForm(instance=ot)
    diagnostico_form = DiagnosticoEvaluacionForm(instance=ot)
    # --- NUEVO: Instancia del formulario para asignar tareas existentes ---
    asignar_tarea_form = AsignarTareaForm()

    if request.method == 'POST':
        # --- Lógica para Cargar Tareas de una Pauta ---
        if 'cargar_tareas_pauta' in request.POST:
            if ot.tipo == 'PREVENTIVA' and ot.pauta_mantenimiento:
                tareas_de_pauta = ot.pauta_mantenimiento.tareas.all()
                ot.tareas_realizadas.add(*tareas_de_pauta)
                
                HistorialOT.objects.create(
                    orden_de_trabajo=ot, usuario=request.user, tipo_evento='MODIFICACION', 
                    descripcion=f"Se cargaron {tareas_de_pauta.count()} tareas desde la pauta '{ot.pauta_mantenimiento.nombre}'."
                )
                messages.success(request, f"Tareas de la pauta '{ot.pauta_mantenimiento.nombre}' cargadas con éxito.")
            else:
                messages.error(request, "Esta acción solo es válida para OTs Preventivas con una pauta asignada.")
            return redirect('ot_detail', pk=ot.pk)

        # --- Lógica para Pausar la OT ---
        elif 'pausar_ot' in request.POST:
            if not es_admin_o_super:
                messages.error(request, "No tienes permiso para pausar la OT.")
            else:
                form = PausarOTForm(request.POST, instance=ot)
                if form.is_valid():
                    instancia = form.save(commit=False)
                    instancia.estado = 'PAUSADA'
                    instancia.save()
                    
                    detalle_pausa = f"Motivo: {instancia.get_motivo_pausa_display()}. Notas: {instancia.notas_pausa or 'N/A'}"
                    HistorialOT.objects.create(
                        orden_de_trabajo=ot, usuario=request.user, tipo_evento='PAUSA', descripcion=detalle_pausa
                    )
                    messages.warning(request, f'La OT #{ot.folio} ha sido pausada.')
                    return redirect('ot_detail', pk=ot.pk)
                else:
                    pausar_form = form

        # --- Lógica para Guardar Diagnóstico ---
        elif 'guardar_diagnostico' in request.POST:
            form = DiagnosticoEvaluacionForm(request.POST, instance=ot)
            if form.is_valid():
                instancia = form.save()
                HistorialOT.objects.create(
                    orden_de_trabajo=ot, usuario=request.user, tipo_evento='MODIFICACION', 
                    descripcion=f"Se añadió/actualizó el diagnóstico: '{instancia.diagnostico_evaluacion}'"
                )
                messages.success(request, 'Diagnóstico guardado con éxito.')
                return redirect('ot_detail', pk=ot.pk)
            else:
                diagnostico_form = form
        
        # --- ¡NUEVA LÓGICA PARA ASIGNAR TAREA EXISTENTE! ---
        elif 'asignar_tarea_existente' in request.POST:
            form = AsignarTareaForm(request.POST)
            if form.is_valid():
                tarea_seleccionada = form.cleaned_data['tarea']
                
                if ot.tareas_realizadas.filter(pk=tarea_seleccionada.pk).exists():
                    messages.warning(request, f'La tarea "{tarea_seleccionada.descripcion}" ya está asignada a esta OT.')
                else:
                    ot.tareas_realizadas.add(tarea_seleccionada)
                    ot.save() # Llama al save de la OT para recalcular costos
                    
                    HistorialOT.objects.create(
                        orden_de_trabajo=ot, usuario=request.user, tipo_evento='MODIFICACION',
                        descripcion=f"Se añadió la tarea: '{tarea_seleccionada.descripcion}'."
                    )
                    messages.success(request, f'Tarea "{tarea_seleccionada.descripcion}" añadida con éxito.')
                
                return redirect('ot_detail', pk=ot.pk)
            else:
                messages.error(request, 'Error al asignar la tarea. Por favor, seleccione una tarea válida.')
                asignar_tarea_form = form # Pasa el formulario con errores de vuelta al contexto

        # --- Lógica para Añadir Insumo Manual ---
        elif 'add_manual_insumo' in request.POST:
            form = ManualInsumoForm(request.POST)
            if form.is_valid():
                nombre = form.cleaned_data['nombre']
                precio = form.cleaned_data['precio_unitario']
                cantidad = form.cleaned_data['cantidad']
                insumo, created = Insumo.objects.get_or_create(nombre=nombre, defaults={'precio_unitario': precio})
                DetalleInsumoOT.objects.create(orden_de_trabajo=ot, insumo=insumo, cantidad=cantidad, repuesto_inventario=None)
                ot.save()
                messages.success(request, f'Insumo manual "{nombre}" añadido con éxito.')
                return redirect('ot_detail', pk=ot.pk)
            else:
                manual_insumo_form = form

        # --- Lógica para Asignar Personal ---
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
        
        # --- Lógica para Cambiar Estado General ---
        elif 'cambiar_estado' in request.POST:
            form = CambiarEstadoOTForm(request.POST, instance=ot)
            if form.is_valid():
                nuevo_estado = form.cleaned_data['estado']
                if ot.estado == 'PAUSADA' and nuevo_estado == 'EN_PROCESO':
                    ot.motivo_pausa, ot.notas_pausa = None, ""
                    HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='REANUDACION', descripcion="La OT ha sido reanudada y puesta 'En Proceso'.")
                if nuevo_estado == 'FINALIZADA' and ot.estado != 'FINALIZADA':
                    ot.fecha_cierre = timezone.now()
                    HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='FINALIZACION', descripcion=f"La OT ha sido finalizada por {request.user.username}.")
                ot.estado = nuevo_estado
                ot.save()
                messages.success(request, f"Estado de la OT actualizado a '{ot.get_estado_display()}'.")
                return redirect('ot_detail', pk=ot.pk)
            else:
                cambiar_estado_form = form
            
        # --- Lógica para Cerrar por Mecánico ---
        elif 'cerrar_mecanico' in request.POST:
            form = CerrarOtMecanicoForm(request.POST, instance=ot)
            if form.is_valid():
                instancia = form.save(commit=False)
                instancia.estado = 'CERRADA_MECANICO'
                instancia.save()
                HistorialOT.objects.create(orden_de_trabajo=ot, usuario=request.user, tipo_evento='CIERRE_MECANICO', descripcion=f"Cerrada por mecánico. Notas: {instancia.motivo_pendiente or 'N/A'}")
                messages.info(request, f"OT #{ot.folio} marcada como 'Cerrada por Mecánico'.")
                return redirect('ot_detail', pk=ot.pk)
            else:
                cerrar_mecanico_form = form

    # Pasar todos los formularios al contexto
    context = {
        'ot': ot,
        'es_admin_o_super': es_admin_o_super,
        'asignar_form': asignar_form,
        'cerrar_mecanico_form': cerrar_mecanico_form,
        'cambiar_estado_form': cambiar_estado_form,
        'manual_insumo_form': manual_insumo_form,
        'pausar_form': pausar_form,
        'diagnostico_form': diagnostico_form,
        # --- ¡NUEVO!: Pasar el formulario de asignar tarea al contexto ---
        'asignar_tarea_form': asignar_tarea_form,
        # Mantenemos 'manual_tarea_form' por si alguna otra parte lo necesita, aunque lo reemplazaremos
        'manual_tarea_form': manual_tarea_form
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
                with transaction.atomic(): # Transacción para asegurar la integridad de los datos
                    
                    # --- Lógica para Vehículos (tu código existente) ---
                    if 'archivo_vehiculos' in request.FILES:
                        # ... (tu código existente para cargar vehículos va aquí y no necesita cambios)
                        # Por brevedad, lo omito, pero debe permanecer en tu archivo.
                        messages.info(request, "Procesando archivo de vehículos...")

                    # --- NUEVA LÓGICA PARA CARGAR TAREAS ---
                    if 'archivo_tareas' in request.FILES:
                        df_tareas = pd.read_excel(request.FILES['archivo_tareas'])
                        
                        tareas_unicas = set()
                        
                        # Identificar todas las columnas de "Novedades"
                        columnas_novedades = [col for col in df_tareas.columns if 'Novedades' in col]

                        # Iterar sobre cada fila del DataFrame
                        for index, row in df_tareas.iterrows():
                            # Iterar sobre cada columna de novedades en la fila actual
                            for col_novedad in columnas_novedades:
                                tarea_bruta = row[col_novedad]
                                if pd.notna(tarea_bruta):
                                    tarea_limpia = _limpiar_descripcion_tarea(tarea_bruta)
                                    if tarea_limpia:
                                        tareas_unicas.add(tarea_limpia)

                        # Ahora, crear las tareas en la base de datos si no existen
                        tareas_creadas = 0
                        tareas_existentes = 0
                        for descripcion_tarea in tareas_unicas:
                            tarea, created = Tarea.objects.get_or_create(
                                descripcion=descripcion_tarea,
                                defaults={
                                    'horas_hombre': 1.0, # Valor por defecto
                                    'costo_base': 0.00   # Valor por defecto
                                }
                            )
                            if created:
                                tareas_creadas += 1
                            else:
                                tareas_existentes += 1
                        
                        messages.success(request, f"Carga de tareas completada: {tareas_creadas} tareas nuevas creadas. {tareas_existentes} tareas ya existían.")

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