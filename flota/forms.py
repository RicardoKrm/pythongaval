# flota/forms.py

from django import forms
from django.contrib.auth.models import User  

from .models import (
    OrdenDeTrabajo, BitacoraDiaria, Vehiculo, Tarea, Insumo, DetalleInsumoOT,
    PautaMantenimiento, ModeloVehiculo, Repuesto, MovimientoStock, Personal # Asegúrate de que Personal esté aquí si lo usas en el futuro
)

class OrdenDeTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = [
            'vehiculo', 
            'tipo', 
            'formato', 
            'kilometraje_apertura', 
            'fecha_programada',
            'prioridad', 
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
            'fecha_programada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prioridad': forms.Select(attrs={'class': 'form-control'}), 
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
        self.fields['fecha_programada'].required = False
        self.fields['prioridad'].required = False 

    def clean(self):
        cleaned_data = super().clean()
        
        tipo_ot = cleaned_data.get('tipo')
        pauta = cleaned_data.get('pauta_mantenimiento')
        tipo_falla = cleaned_data.get('tipo_falla')
        sintomas = cleaned_data.get('sintomas_reportados')

        if tipo_ot == 'PREVENTIVA' and not pauta:
            self.add_error('pauta_mantenimiento', 'Para una OT Preventiva, debe seleccionar una pauta.')
        if tipo_ot != 'PREVENTIVA' and pauta:
            self.add_error('pauta_mantenimiento', 'Las pautas solo se pueden asignar a Órdenes de Trabajo de tipo PREVENTIVA.')
        if tipo_ot in ['CORRECTIVA', 'EVALUATIVA'] and not tipo_falla:
            self.add_error('tipo_falla', 'Para este tipo de OT, debe especificar un tipo de falla.')
        if tipo_ot == 'PREVENTIVA' and tipo_falla:
            self.add_error('tipo_falla', 'El tipo de falla solo se aplica a OTs Correctivas o Evaluativas.')
        if tipo_ot == 'EVALUATIVA' and not sintomas:
            self.add_error('sintomas_reportados', 'Para una OT Evaluativa, debe describir los síntomas reportados.')
        if tipo_ot != 'EVALUATIVA' and sintomas:
            self.add_error('sintomas_reportados', 'Los síntomas solo se aplican a Órdenes de Trabajo de tipo EVALUATIVA.')

        return cleaned_data


class CambiarEstadoOTForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['estado']
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }


class BitacoraDiariaForm(forms.ModelForm):
    class Meta:
        model = BitacoraDiaria
        fields = '__all__'
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control select2'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class CargaMasivaForm(forms.Form):
    archivo_vehiculos = forms.FileField(
        label="Archivo Excel de Vehículos", 
        required=False, 
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    archivo_pautas = forms.FileField(
        label="Archivo Excel de Pautas", 
        required=False, 
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    archivo_historial = forms.FileField(
        label="Archivo Excel de Historial de Mantenimientos", 
        required=False, 
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    # --- Nuevos campos añadidos ---
    archivo_tipos_falla = forms.FileField(
        label="Archivo Excel de Tipos de Falla (Pareto)", 
        required=False, 
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    archivo_tareas = forms.FileField(
        label="Archivo Excel de Tareas (Bitácoras)", 
        required=False, 
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )


class CerrarOtMecanicoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['kilometraje_cierre', 'motivo_pendiente']
        widgets = {
            'kilometraje_cierre': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo_pendiente': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AsignarPersonalOTForm(forms.ModelForm):
    responsable = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor']),
        widget=forms.Select(attrs={'class': 'select2', 'style': 'width: 100%;'}), 
        label="Responsable Principal",
        required=False
    )
    personal_asignado = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor', 'Asistente']),
        widget=forms.SelectMultiple(attrs={'class': 'select2', 'style': 'width: 100%;'}),
        label="Personal de Apoyo (Ayudantes)",
        required=False
    )

    class Meta:
        model = OrdenDeTrabajo
        fields = ['responsable', 'personal_asignado']

class ManualTareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ['descripcion', 'horas_hombre', 'costo_base']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'horas_hombre': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_base': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ManualInsumoForm(forms.Form): # <<-- CAMBIO AQUÍ: de forms.ModelForm a forms.Form
    nombre = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Nombre del Insumo" # Añadido label para claridad
    )
    precio_unitario = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        initial=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Precio Unitario" # Añadido label para claridad
    )
    cantidad = forms.DecimalField(
        min_value=0.01, # Asegura que la cantidad sea al menos un pequeño valor positivo
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Cantidad" # Añadido label para claridad
    )

class FiltroPizarraForm(forms.Form):
    modelo = forms.ModelChoiceField(queryset=ModeloVehiculo.objects.all(), required=False, label="Modelo", widget=forms.Select(attrs={'class': 'form-control'}))
    tipo_mantenimiento = forms.CharField(required=False, label="Tipo de Pauta", widget=forms.TextInput(attrs={'class': 'form-control'}))
    proximos_5000_km = forms.BooleanField(required=False, label="Próximos 5.000 KM", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

class PausarOTForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['motivo_pausa', 'notas_pausa']
        widgets = {
            'motivo_pausa': forms.Select(attrs={'class': 'form-control'}),
            'notas_pausa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Especifique el motivo si seleccionó "Otro"...'}),
        }
        
class DiagnosticoEvaluacionForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['diagnostico_evaluacion']
        widgets = {
            'diagnostico_evaluacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ingrese el diagnóstico técnico aquí...'}),
        }

class OTFiltroForm(forms.Form):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.all(), 
        required=False,
        label="Vehículo",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    tipo = forms.ChoiceField(
        choices=[('', 'Todos los Tipos')] + OrdenDeTrabajo.TIPO_CHOICES,
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
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.all(), 
        required=False,
        label="Filtrar por Vehículo",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los Estados')] + OrdenDeTrabajo.ESTADO_CHOICES,
        required=False, 
        label="Filtrar por Estado",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    responsable = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor']).distinct(),
        required=False,
        label="Filtrar por Responsable",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )    
    repuestos_disponibles = forms.ChoiceField(
        choices=[
            ('', 'Todos los Repuestos'),
            ('true', 'Con Repuestos Disponibles'),
            ('false', 'Faltan Repuestos')
        ],
        required=False,
        label='Disponibilidad de Repuestos',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class RepuestoForm(forms.ModelForm):
    class Meta:
        model = Repuesto
        fields = [
            'nombre',
            'numero_parte',
            'calidad',
            'stock_actual',
            'stock_minimo',
            'ubicacion',
            'proveedor_habitual',
            'precio_unitario' # ESTA LÍNEA DEBE EXISTIR SOLO SI YA SE MIGRÓ EL CAMPO EN models.py
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_parte': forms.TextInput(attrs={'class': 'form-control'}),
            'calidad': forms.Select(attrs={'class': 'form-control'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'proveedor_habitual': forms.Select(attrs={'class': 'form-control select2'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control'}), # ESTA LÍNEA DEBE EXISTIR SOLO SI YA SE MIGRÓ EL CAMPO EN models.py
        }    
    
    # AÑADIR ESTE MÉTODO __init__ para manejar el campo precio_unitario
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que precio_unitario no sea un campo requerido a nivel de formulario,
        # permitiendo que use el default=0 del modelo si se deja vacío.
        if 'precio_unitario' in self.fields: # Asegura que el campo exista antes de intentar modificarlo
            self.fields['precio_unitario'].required = False


class MovimientoStockForm(forms.ModelForm):
    class Meta:
        model = MovimientoStock
        exclude = ['usuario_responsable', 'orden_de_trabajo', 'repuesto']
        widgets = {
            'tipo_movimiento': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 10 para entradas, -2 para salidas'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad == 0:
            raise forms.ValidationError("La cantidad no puede ser cero.")
        return cantidad