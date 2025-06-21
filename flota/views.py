# flota/views.py


from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required, user_passes_test

from django.db.models import Min, Sum, Count, F, Q

from django.db.models.functions import TruncMonth

from django.http import HttpResponse

from django.template.loader import render_to_string

from django.db import connection, transaction

from django.contrib import messages

from weasyprint import HTML

import json

import pandas as pd

from datetime import datetime, timedelta


# Se importan TODOS los modelos y formularios necesarios

from .models import (

    Vehiculo, PautaMantenimiento, OrdenDeTrabajo, BitacoraDiaria, ModeloVehiculo

)

from .forms import (

    OrdenDeTrabajoForm, AddTareaToOTForm, AddInsumoToOTForm,

    CambiarEstadoOTForm, BitacoraDiariaForm, CargaMasivaForm, CerrarOtMecanicoForm

)


# --- Función de chequeo de rol ---

def es_supervisor_o_admin(user):

    return user.groups.filter(name__in=['Supervisor', 'Administrador']).exists()



# --- Vistas del Dashboard y Flota ---


# flota/views.py
# (Asegúrate de tener importados 'datetime', 'timedelta' y 'random' al principio)
from datetime import datetime, timedelta
import random

# ...

@login_required
def dashboard_flota(request):
    connection.set_tenant(request.tenant)
    vehiculos = Vehiculo.objects.all().order_by('numero_interno')
    
    data_flota = []
    for vehiculo in vehiculos:
        # --- CÁLCULO DE KM PROMEDIO DIARIO ---
        # Para una demo, usaremos un valor aleatorio.
        # En una versión real, esto se calcularía con registros históricos de la bitácora.
        km_prom_dia = random.randint(150, 450)
        # -------------------------------------
        
        km_actual = vehiculo.kilometraje_actual
        proxima_pauta_agg = PautaMantenimiento.objects.filter(
            modelo_vehiculo=vehiculo.modelo,
            kilometraje_pauta__gt=km_actual
        ).aggregate(proximo_km=Min('kilometraje_pauta'))
        proximo_km_pauta = proxima_pauta_agg.get('proximo_km')
        
        estado = "NORMAL"
        kms_faltantes = None
        pauta_obj = None
        fecha_prox_mant = None # Inicializamos la variable

        if proximo_km_pauta:
            try:
                pauta_obj = PautaMantenimiento.objects.get(
                    modelo_vehiculo=vehiculo.modelo, 
                    kilometraje_pauta=proximo_km_pauta
                )
                tolerancia = 1000
                advertencia = 5000
                kms_faltantes = proximo_km_pauta - km_actual
                
                if kms_faltantes <= tolerancia:
                    estado = "VENCIDO"
                elif kms_faltantes <= advertencia:
                    estado = "PROXIMO"

                # --- CÁLCULO DE FECHA DE PRONÓSTICO ---
                if km_prom_dia > 0 and kms_faltantes > 0:
                    dias_para_pauta = kms_faltantes / km_prom_dia
                    fecha_prox_mant = datetime.now().date() + timedelta(days=dias_para_pauta)
                # ---------------------------------------

            except PautaMantenimiento.DoesNotExist:
                pauta_obj = None

        data_flota.append({
            'vehiculo': vehiculo,
            'proxima_pauta_obj': pauta_obj,
            'proximo_km': proximo_km_pauta,
            'kms_faltantes': kms_faltantes,
            'estado': estado,
            'km_prom_dia': km_prom_dia,         # <-- Dato nuevo
            'fecha_prox_mant': fecha_prox_mant, # <-- Dato nuevo
        })

    context = {
        'data_flota': data_flota,
        'tenant_name': request.tenant.nombre,
    }
    return render(request, 'flota/dashboard.html', context)



@login_required


def orden_trabajo_list(request):

    connection.set_tenant(request.tenant)

    # Si la URL incluye un 'vehiculo_id', lo usamos para inicializar el formulario
    initial_data = {}
    vehiculo_id = request.GET.get('vehiculo_id')
    if vehiculo_id:
        initial_data['vehiculo'] = vehiculo_id
        initial_data['tipo'] = 'CORRECTIVA' # Pre-seleccionamos el tipo también

    if request.method == 'POST':
        form = OrdenDeTrabajoForm(request.POST)
        if form.is_valid():
            ot = form.save()
            messages.success(request, f'Orden de Trabajo #{ot.folio} creada con éxito.')
            return redirect('ot_list')
    else:
        # Pasamos los datos iniciales al formulario
        form = OrdenDeTrabajoForm(initial=initial_data)

    ordenes = OrdenDeTrabajo.objects.all().order_by('-fecha_creacion')
    context = {'ordenes': ordenes, 'form': form}
    return render(request, 'flota/orden_trabajo_list.html', context)



@login_required

def orden_trabajo_detail(request, pk):

    connection.set_tenant(request.tenant)

    ot = get_object_or_404(OrdenDeTrabajo, pk=pk)

    es_admin_o_super = request.user.groups.filter(name__in=['Administrador', 'Supervisor']).exists()

    if request.method == 'POST':

        if 'add_tarea' in request.POST:

            tarea_form = AddTareaToOTForm(request.POST)

            if tarea_form.is_valid():

                ot.tareas_realizadas.add(tarea_form.cleaned_data['tarea'])

                ot.save()

                messages.success(request, '¡Tarea añadida con éxito!')

                return redirect('flota:ot_detail', pk=ot.pk)

        elif 'add_insumo' in request.POST:

            insumo_form = AddInsumoToOTForm(request.POST)

            if insumo_form.is_valid():

                detalle_insumo = insumo_form.save(commit=False)

                detalle_insumo.orden_de_trabajo = ot

                detalle_insumo.save()

                ot.save()

                messages.success(request, '¡Insumo añadido con éxito!')

                return redirect('flota:ot_detail', pk=ot.pk)

        elif 'cerrar_mecanico' in request.POST:

            form = CerrarOtMecanicoForm(request.POST, instance=ot)

            if form.is_valid():

                instancia = form.save(commit=False)

                instancia.estado = 'CERRADA_MECANICO'

                instancia.save()

                messages.info(request, f"OT #{ot.folio} marcada como 'Cerrada por Mecánico'. El supervisor será notificado para su revisión final.")

                return redirect('flota:ot_detail', pk=ot.pk)

    tarea_form = AddTareaToOTForm()

    insumo_form = AddInsumoToOTForm()

    cerrar_mecanico_form = CerrarOtMecanicoForm(instance=ot)

    context = {'ot': ot, 'tarea_form': tarea_form, 'insumo_form': insumo_form, 'cerrar_mecanico_form': cerrar_mecanico_form, 'es_admin_o_super': es_admin_o_super}

    return render(request, 'flota/orden_trabajo_detail.html', context)



@login_required

def bitacora_diaria_list(request):

    connection.set_tenant(request.tenant)

    if request.method == 'POST':

        form = BitacoraDiariaForm(request.POST)

        if form.is_valid():

            BitacoraDiaria.objects.update_or_create(

                vehiculo=form.cleaned_data['vehiculo'],

                fecha=form.cleaned_data['fecha'],

                defaults=form.cleaned_data

            )

            messages.success(request, f"Registro de bitácora para el vehículo {form.cleaned_data['vehiculo'].numero_interno} en la fecha {form.cleaned_data['fecha']} guardado.")

            return redirect('bitacora_list')

    else:

        form = BitacoraDiariaForm()

    bitacoras = BitacoraDiaria.objects.all().order_by('-fecha', 'vehiculo__numero_interno')[:50]

    context = {'form': form, 'bitacoras': bitacoras}

    return render(request, 'flota/bitacora_list.html', context)



@login_required

@user_passes_test(es_supervisor_o_admin)

def carga_masiva(request):

    connection.set_tenant(request.tenant)

    if request.method == 'POST':

        form = CargaMasivaForm(request.POST, request.FILES)

        if form.is_valid():

            try:

                with transaction.atomic():

                    if 'archivo_vehiculos' in request.FILES:

                        df_v = pd.read_excel(request.FILES['archivo_vehiculos'], header=1)

                        df_v.columns = df_v.columns.str.strip()

                        df_v = df_v.dropna(subset=['N° INT.'])

                        count = 0

                        for _, row in df_v.iterrows():

                            try:

                                modelo, _ = ModeloVehiculo.objects.get_or_create(nombre=str(row['MODELO']).strip(), defaults={'marca': str(row['MARCA']).strip(), 'tipo': str(row['TIPO VEH.']).strip()})

                                Vehiculo.objects.update_or_create(numero_interno=str(int(row['N° INT.'])).strip(), defaults={'patente': str(row.get('PPU', '')).strip(), 'modelo': modelo, 'kilometraje_actual': int(row['KM ACTUAL'])})

                                count += 1

                            except (ValueError, KeyError) as e:

                                messages.warning(request, f"Se omitió una fila de vehículos por datos inválidos: {e}")

                        messages.success(request, f"{count} registros de vehículos procesados.")

            except Exception as e:

                messages.error(request, f"Ocurrió un error durante la carga: {e}")

            return redirect('flota:carga_masiva')

    else:

        form = CargaMasivaForm()

    context = {'form': form}

    return render(request, 'flota/carga_masiva.html', context)



# --- Vistas de KPIs y Análisis ---


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

    # --- NUEVA LÓGICA DE FILTRO DE FECHAS ---
    # Por defecto, mostramos los últimos 30 días
    end_date_str = request.GET.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Si las fechas son inválidas, volvemos a los valores por defecto
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
    # ----------------------------------------

    # Aplicamos el filtro de fecha a la consulta principal
    fallas = OrdenDeTrabajo.objects.filter(
        tipo='CORRECTIVA',
        tipo_falla__isnull=False,
        tfs_minutos__gt=0,
        fecha_creacion__date__range=[start_date, end_date] # <-- FILTRO APLICADO
    ).values(
        'tipo_falla__descripcion', 'tipo_falla__causa', 'tipo_falla__criticidad'
    ).annotate(
        tfs_total_falla=Sum('tfs_minutos')
    ).order_by('-tfs_total_falla')
    
    # ... (El resto de la lógica de cálculo del Pareto se mantiene igual) ...
    tfs_gran_total = sum(item['tfs_total_falla'] for item in fallas)
    frec_acumulada = 0
    data_pareto = []
    for item in fallas:
        frec_relativa = (item['tfs_total_falla'] / tfs_gran_total) * 100 if tfs_gran_total > 0 else 0
        frec_acumulada += frec_relativa
        item['frecuencia_relativa'] = round(frec_relativa, 2)
        item['frecuencia_acumulada'] = round(frec_acumulada, 2)
        data_pareto.append(item)

    context = {
        'data_pareto_tabla': data_pareto,
        'labels': json.dumps([item['tipo_falla__descripcion'] for item in data_pareto]),
        'frecuencia_data': json.dumps([item['frecuencia_relativa'] for item in data_pareto]),
        'acumulada_data': json.dumps([item['frecuencia_acumulada'] for item in data_pareto]),
        # Pasamos las fechas al template para que los campos del filtro recuerden su valor
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'flota/analisis_fallas.html', context)



@login_required

def analisis_avanzado(request):

    connection.set_tenant(request.tenant)

    tco_data = OrdenDeTrabajo.objects.filter(proveedor__isnull=False, costo_total__gt=0, kilometraje_cierre__isnull=False).values('proveedor__nombre').annotate(costo_sum=Sum('costo_total'), km_recorrido_sum=Sum(F('kilometraje_cierre') - F('kilometraje_apertura'))).order_by('-costo_sum')

    for item in tco_data:

        item['costo_por_km'] = (item['costo_sum'] / item['km_recorrido_sum']) if item['km_recorrido_sum'] and item['km_recorrido_sum'] > 0 else 0

    tendencia_ots = OrdenDeTrabajo.objects.annotate(month=TruncMonth('fecha_creacion')).values('month').annotate(preventivas_total=Count('id', filter=Q(tipo='PREVENTIVA')), correctivas_total=Count('id', filter=Q(tipo='CORRECTIVA')), preventivas_ok=Count('id', filter=Q(tipo='PREVENTIVA', estado='FINALIZADA')), correctivas_ok=Count('id', filter=Q(tipo='CORRECTIVA', estado='FINALIZADA'))).order_by('month')

    labels_tendencia = [t['month'].strftime('%b %Y') for t in tendencia_ots]

    preventivas_total_data = [t['preventivas_total'] for t in tendencia_ots]

    correctivas_total_data = [t['correctivas_total'] for t in tendencia_ots]

    preventivas_ok_data = [t['preventivas_ok'] for t in tendencia_ots]

    correctivas_ok_data = [t['correctivas_ok'] for t in tendencia_ots]

    context = {

        'tco_data': tco_data, 'labels_tendencia': json.dumps(labels_tendencia),

        'preventivas_total_data': json.dumps(preventivas_total_data), 'correctivas_total_data': json.dumps(correctivas_total_data),

        'preventivas_ok_data': json.dumps(preventivas_ok_data), 'correctivas_ok_data': json.dumps(correctivas_ok_data),

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

    return redirect('flota:ot_detail', pk=ot.pk)



@login_required

def generar_ot_pdf(request, pk):

    connection.set_tenant(request.tenant)

    ot = get_object_or_404(OrdenDeTrabajo, pk=pk)

    html_string = render_to_string('flota/ot_pdf_template.html', {'ot': ot, 'request': request})

    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    response['Content-Disposition'] = f'inline; filename="OT-{ot.pk}.pdf"'

    return response 

# flota/views.py

# ... (todas las vistas existentes se quedan como están) ...

# --- AÑADE ESTA VISTA FALTANTE AL FINAL DEL ARCHIVO ---

@login_required
def actualizar_km_vehiculo(request, pk):
    """
    Procesa la actualización de kilometraje de un vehículo desde el modal del dashboard.
    """
    connection.set_tenant(request.tenant)
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    
    if request.method == 'POST':
        nuevo_km = request.POST.get('kilometraje_actual')
        
        if nuevo_km and nuevo_km.isdigit():
            # Solo actualizamos el kilometraje. Django se encarga de la fecha automáticamente.
            vehiculo.kilometraje_actual = int(nuevo_km)
            # update_fields es más eficiente porque solo actualiza ese campo
            vehiculo.save(update_fields=['kilometraje_actual'])
            messages.success(request, f"Kilometraje del vehículo {vehiculo.numero_interno} actualizado a {nuevo_km} KM.")
        else:
            messages.error(request, "El kilometraje ingresado no es válido.")

    # Siempre redirigimos de vuelta al dashboard después de la acción
    return redirect('dashboard')

# flota/views.py
# ...

@login_required
def historial_vehiculo(request, pk):
    connection.set_tenant(request.tenant)
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    
    # Buscamos todas las OTs para este vehículo, de la más reciente a la más antigua
    ordenes = OrdenDeTrabajo.objects.filter(vehiculo=vehiculo).order_by('-fecha_creacion')
    
    context = {
        'vehiculo': vehiculo,
        'ordenes': ordenes,
    }
    return render(request, 'flota/historial_vehiculo.html', context)