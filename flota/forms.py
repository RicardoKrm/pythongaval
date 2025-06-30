from django import forms
from django.contrib.auth.models import User  

from .models import (
    OrdenDeTrabajo, BitacoraDiaria, Vehiculo, Tarea, Insumo, DetalleInsumoOT,
    PautaMantenimiento, ModeloVehiculo 
)

# --- FORMULARIOS EXISTENTES (MODIFICADOS Y CONSERVADOS) ---
class OrdenDeTrabajoForm(forms.ModelForm):
    """
    Formulario para la CREACIÓN de una nueva Orden de Trabajo.
    Ahora incluye validación en el backend para las reglas de negocio.
    """
    class Meta:
        model = OrdenDeTrabajo
        fields = [
            'vehiculo', 
            'tipo', 
            'formato', 
            'kilometraje_apertura', 
            'pauta_mantenimiento',
            'tipo_falla',
            'observacion_inicial',
            'sintomas_reportados',
        ]
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'formato': forms.Select(attrs={'class': 'form-control'}),
            'kilometraje_apertura': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'KM al abrir OT'}),
            'pauta_mantenimiento': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'tipo_falla': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'observacion_inicial': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones o motivo de la OT...'}),
            'sintomas_reportados': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Síntomas reportados por el conductor...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pauta_mantenimiento'].required = False
        self.fields['tipo_falla'].required = False
        self.fields['sintomas_reportados'].required = False

    # ---> INICIO DEL BLOQUE NUEVO: MÉTODO CLEAN() <---
    def clean(self):
        # Primero, obtenemos los datos "limpios" del formulario
        cleaned_data = super().clean()
        
        # Obtenemos el tipo de OT seleccionado por el usuario
        tipo_ot = cleaned_data.get('tipo')
        
        # Obtenemos los campos que queremos validar
        pauta = cleaned_data.get('pauta_mantenimiento')
        tipo_falla = cleaned_data.get('tipo_falla')
        sintomas = cleaned_data.get('sintomas_reportados')

        # --- REGLA 1: Pautas solo para OTs Preventivas ---
        if tipo_ot == 'PREVENTIVA' and not pauta:
            # Si es PREVENTIVA, la pauta es OBLIGATORIA
            self.add_error('pauta_mantenimiento', 'Para una OT Preventiva, debe seleccionar una pauta.')
        
        if tipo_ot != 'PREVENTIVA' and pauta:
            # Si NO es PREVENTIVA, no debe tener pauta
            self.add_error('pauta_mantenimiento', 'Las pautas solo se pueden asignar a Órdenes de Trabajo de tipo PREVENTIVA.')

        # --- REGLA 2: Tipo de Falla solo para OTs Correctivas/Evaluativas ---
        if tipo_ot in ['CORRECTIVA', 'EVALUATIVA'] and not tipo_falla:
            # Si es CORRECTIVA o EVALUATIVA, el tipo de falla es OBLIGATORIO
            self.add_error('tipo_falla', 'Para este tipo de OT, debe especificar un tipo de falla.')

        if tipo_ot == 'PREVENTIVA' and tipo_falla:
            # Si es PREVENTIVA, no debe tener tipo de falla
            self.add_error('tipo_falla', 'El tipo de falla solo se aplica a OTs Correctivas o Evaluativas.')

        # --- REGLA 3: Síntomas solo para OTs Evaluativas ---
        if tipo_ot == 'EVALUATIVA' and not sintomas:
            # Si es EVALUATIVA, los síntomas son OBLIGATORIOS
            self.add_error('sintomas_reportados', 'Para una OT Evaluativa, debe describir los síntomas reportados.')
        
        if tipo_ot != 'EVALUATIVA' and sintomas:
             # Si NO es EVALUATIVA, no debe tener síntomas
            self.add_error('sintomas_reportados', 'Los síntomas solo se aplican a Órdenes de Trabajo de tipo EVALUATIVA.')

        # Devolvemos los datos limpios para que Django continúe el proceso
        return cleaned_data


class CambiarEstadoOTForm(forms.ModelForm):
    """
    Formulario para que un Supervisor/Admin cambie el estado general de la OT.
    Ahora incluye el estado 'PAUSADA', pero lo manejaremos con un form específico.
    """
    class Meta:
        model = OrdenDeTrabajo
        fields = ['estado']
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }


class BitacoraDiariaForm(forms.ModelForm):
    # Sin cambios en este formulario
    class Meta:
        model = BitacoraDiaria
        fields = '__all__'
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control select2'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class CargaMasivaForm(forms.Form):
    # Sin cambios en este formulario
    archivo_vehiculos = forms.FileField(label="Archivo Excel de Vehículos", required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    archivo_pautas = forms.FileField(label="Archivo Excel de Pautas", required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    archivo_historial = forms.FileField(label="Archivo Excel de Historial de Mantenimientos", required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

class CerrarOtMecanicoForm(forms.ModelForm):
    """
    Formulario para que el mecánico cierre su parte del trabajo.
    Usa el campo 'motivo_pendiente' que ya existía.
    """
    class Meta:
        model = OrdenDeTrabajo
        fields = ['kilometraje_cierre', 'motivo_pendiente']
        widgets = {
            'kilometraje_cierre': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo_pendiente': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
class AsignarPersonalOTForm(forms.ModelForm):
    # Usamos ModelChoiceField para filtrar y mostrar solo usuarios que son mecánicos o supervisores.
    responsable = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor']),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False
    )
    personal_asignado = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor', 'Asistente']),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        required=False
    )

    class Meta:
        model = OrdenDeTrabajo
        fields = ['responsable', 'personal_asignado']

class ManualTareaForm(forms.ModelForm):
    # Sin cambios en este formulario
    class Meta:
        model = Tarea
        fields = ['descripcion', 'horas_hombre', 'costo_base']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'horas_hombre': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_base': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ManualInsumoForm(forms.ModelForm):
    # Sin cambios en este formulario, pero añadimos el campo cantidad que faltaba
    cantidad = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    class Meta:
        model = Insumo
        fields = ['nombre', 'precio_unitario', 'cantidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class FiltroPizarraForm(forms.Form):
    # Sin cambios en este formulario
    modelo = forms.ModelChoiceField(queryset=ModeloVehiculo.objects.all(), required=False, label="Modelo", widget=forms.Select(attrs={'class': 'form-control'}))
    tipo_mantenimiento = forms.CharField(required=False, label="Tipo de Pauta", widget=forms.TextInput(attrs={'class': 'form-control'}))
    proximos_5000_km = forms.BooleanField(required=False, label="Próximos 5.000 KM", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


# --- NUEVOS FORMULARIOS ---

class PausarOTForm(forms.ModelForm):
    """
    Formulario específico para gestionar la pausa de una OT.
    Solo un Supervisor/Admin podrá usarlo.
    """
    class Meta:
        model = OrdenDeTrabajo
        fields = ['motivo_pausa', 'notas_pausa']
        widgets = {
            'motivo_pausa': forms.Select(attrs={'class': 'form-control'}),
            'notas_pausa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Especifique el motivo si seleccionó "Otro"...'}),
        }
        
class DiagnosticoEvaluacionForm(forms.ModelForm):
    """
    Formulario para que el mecánico añada el diagnóstico a una OT Evaluativa.
    """
    class Meta:
        model = OrdenDeTrabajo
        fields = ['diagnostico_evaluacion']
        widgets = {
            'diagnostico_evaluacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ingrese el diagnóstico técnico aquí...'}),
        }

# En flota/forms.py

# ... (tus otros formularios) ...

class OTFiltroForm(forms.Form):
    # Usamos campos no requeridos (required=False) para que el filtro sea opcional
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.all(), 
        required=False,
        label="Vehículo",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    tipo = forms.ChoiceField(
        choices=[('', 'Todos los Tipos')] + OrdenDeTrabajo.TIPO_CHOICES, # Añadimos una opción "Todos"
        required=False, 
        label="Tipo de OT",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los Estados')] + OrdenDeTrabajo.ESTADO_CHOICES,
        required=False, 
        label="Estado",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fecha_desde = forms.DateField(
        required=False, 
        label="Fecha Desde",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    fecha_hasta = forms.DateField(
        required=False, 
        label="Fecha Hasta",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class CalendarioFiltroForm(forms.Form):
    # Usamos campos no requeridos para que el filtro sea opcional
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.all(), 
        required=False,
        label="Filtrar por Vehículo",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los Estados')] + OrdenDeTrabajo.ESTADO_CHOICES,
        required=False, 
        label="Filtrar por Estado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    responsable = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor']),
        required=False,
        label="Filtrar por Responsable",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )

class CalendarioFiltroForm(forms.Form):
    # Usamos campos no requeridos (required=False) para que el filtro sea opcional
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.all(), 
        required=False,
        label="Filtrar por Vehículo",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los Estados')] + OrdenDeTrabajo.ESTADO_CHOICES, # Añadimos una opción "Todos"
        required=False, 
        label="Filtrar por Estado",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    responsable = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor']).distinct(), # Filtramos por rol
        required=False,
        label="Filtrar por Responsable",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )    