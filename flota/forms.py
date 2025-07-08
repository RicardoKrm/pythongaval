# flota/forms.py

from django import forms
from django.contrib.auth.models import User  
from django.contrib.auth.models import Group

from .models import (
    OrdenDeTrabajo, BitacoraDiaria, Vehiculo, Tarea, Insumo, DetalleInsumoOT,
    PautaMantenimiento, ModeloVehiculo, Repuesto, MovimientoStock, Personal,
    Ruta, CondicionAmbiental, CargaCombustible # <-- ASEGÚRATE DE QUE ESTÉ AQUÍ
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

# flota/forms.py

# ... (tus imports existentes) ...

class CargaMasivaForm(forms.Form):
    # Campos que se mantienen y sus etiquetas actualizadas
    archivo_vehiculos = forms.FileField(
        label="Archivo Excel de Flota (Vehículos)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'custom-input'})
    )
    archivo_pautas = forms.FileField(
        label="Archivo Excel de Pautas de Mantenimiento",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'custom-input'})
    )
    archivo_repuestos = forms.FileField(
        label="Archivo Excel de Inventario de Repuestos",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'custom-input'})
    )
    # NUEVOS CAMPOS
    archivo_historial_mantenimiento = forms.FileField(
        label="Archivo Excel de Historial de OTs Finalizadas",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'custom-input'})
    )
    archivo_bitacoras_diarias = forms.FileField(
        label="Archivo Excel de Bitácoras Diarias",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'custom-input'})
    )

    # El resto de los campos antiguos (tipos_falla, tareas) se eliminan.
    
class CerrarOtMecanicoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['kilometraje_cierre', 'motivo_pendiente']
        widgets = {
            'kilometraje_cierre': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo_pendiente': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AsignarPersonalOTForm(forms.ModelForm):
    # Definimos los campos aquí para que siempre existan en la clase
    responsable = forms.ModelChoiceField(
        queryset=User.objects.none(), # Empezamos con un queryset vacío
        required=False,
        label="Responsable Principal",
        widget=forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'})
    )
    personal_asignado = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(), # Empezamos con un queryset vacío
        required=False,
        label="Personal de Apoyo (Ayudantes)",
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'style': 'width: 100%;'})
    )

    class Meta:
        model = OrdenDeTrabajo
        fields = ['responsable', 'personal_asignado'] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- ESTA ES LA PARTE QUE SE MANTIENE PERO AHORA ES MÁS ROBUSTA ---
        # Ahora, en lugar de crear los campos, simplemente actualizamos sus querysets.
        
        roles_permitidos = Group.objects.filter(name__in=['Mecánico', 'Supervisor', 'Administrador'])
        usuarios_asignables = User.objects.filter(groups__in=roles_permitidos).distinct().order_by('username')
        
        self.fields['responsable'].queryset = usuarios_asignables
        self.fields['personal_asignado'].queryset = usuarios_asignables

class ManualTareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        # Usamos el nuevo nombre del campo: 'tiempo_estandar_minutos'
        fields = ['descripcion', 'tiempo_estandar_minutos', 'costo_base']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'tiempo_estandar_minutos': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 90'}),
            'costo_base': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'tiempo_estandar_minutos': 'Tiempo Estándar (minutos)',
            'costo_base': 'Costo Mano de Obra ($)'
        }

# --- ¡NUEVA CLASE A AÑADIR! ---
class AsignarTareaForm(forms.Form):
    """
    Formulario para seleccionar una Tarea existente y asignarla a una OT.
    """
    tarea = forms.ModelChoiceField(
        queryset=Tarea.objects.all().order_by('descripcion'), # Obtiene todas las tareas y las ordena alfabéticamente
        label="Seleccionar Tarea de la Lista",
        widget=forms.Select(attrs={
            'class': 'form-control select2', # Usa la clase 'select2' para un menú con buscador
            'style': 'width: 100%;'
        }),
        help_text="Seleccione una tarea predefinida del catálogo."
    )

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
    modelo = forms.ModelChoiceField(
        queryset=ModeloVehiculo.objects.all().order_by('nombre'),
        required=False,
        label="Modelo",
        empty_label="Todos los Modelos",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    tipo_mantenimiento = forms.ChoiceField(
        required=False,
        label="Tipo de Mantenimiento",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    proximos_5000_km = forms.BooleanField(
        required=False,
        label="Próximos 5.000 KM",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pautas = PautaMantenimiento.objects.order_by('nombre').values_list('nombre', 'nombre').distinct()
        opciones_finales = [('', 'Todos los Tipos')] + list(pautas)
        self.fields['tipo_mantenimiento'].choices = opciones_finales

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

# flota/forms.py

# ... (tus imports existentes) ...

class CalendarioFiltroForm(forms.Form):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.all(), 
        required=False,
        label="Filtrar por Vehículo",
        widget=forms.Select(attrs={'class': 'custom-input select2'}) # CAMBIO AQUÍ
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los Estados')] + OrdenDeTrabajo.ESTADO_CHOICES,
        required=False, 
        label="Filtrar por Estado",
        widget=forms.Select(attrs={'class': 'custom-input'}) # CAMBIO AQUÍ
    )
    responsable = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name__in=['Mecánico', 'Supervisor']).distinct(),
        required=False,
        label="Filtrar por Responsable",
        widget=forms.Select(attrs={'class': 'custom-input select2'}) # CAMBIO AQUÍ
    )    
    repuestos_disponibles = forms.ChoiceField(
        choices=[
            ('', 'Todos los Repuestos'),
            ('true', 'Con Repuestos Disponibles'),
            ('false', 'Faltan Repuestos')
        ],
        required=False,
        label='Disponibilidad de Repuestos',
        widget=forms.Select(attrs={'class': 'custom-input'}) # CAMBIO AQUÍ
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
    
class CargaCombustibleForm(forms.ModelForm):
    # Campos adicionales para crear un objeto CondicionAmbiental sobre la marcha
    temperatura_celsius = forms.IntegerField(
        label="Temperatura (°C)", 
        initial=15,
        widget=forms.NumberInput(attrs={'class': 'custom-input'}) # CAMBIO AQUÍ
    )
    condicion_climatica = forms.ChoiceField(
        choices=CondicionAmbiental.CLIMA_CHOICES, 
        label="Condición Climática",
        widget=forms.Select(attrs={'class': 'custom-input'}) # CAMBIO AQUÍ
    )
    nivel_trafico = forms.ChoiceField(
        choices=CondicionAmbiental.TRAFICO_CHOICES,
        label="Nivel de Tráfico",
        widget=forms.Select(attrs={'class': 'custom-input'}) # CAMBIO AQUÍ
    )

    class Meta:
        model = CargaCombustible
        fields = [
            'vehiculo', 
            'conductor', 
            'ruta', 
            'fecha_carga', 
            'kilometraje_en_carga', 
            'litros_cargados',
            'costo_por_litro',
            'costo_total_carga',
            'es_tanque_lleno',
        ]
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'custom-input select2', 'style': 'width: 100%;'}), # CAMBIO AQUÍ
            'conductor': forms.Select(attrs={'class': 'custom-input select2', 'style': 'width: 100%;'}), # CAMBIO AQUÍ
            'ruta': forms.Select(attrs={'class': 'custom-input select2', 'style': 'width: 100%;'}), # CAMBIO AQUÍ
            'fecha_carga': forms.DateTimeInput(attrs={'class': 'custom-input', 'type': 'datetime-local'}), # CAMBIO AQUÍ
            'kilometraje_en_carga': forms.NumberInput(attrs={'class': 'custom-input'}), # CAMBIO AQUÍ
            'litros_cargados': forms.NumberInput(attrs={'class': 'custom-input'}), # CAMBIO AQUÍ
            'costo_por_litro': forms.NumberInput(attrs={'class': 'custom-input'}), # CAMBIO AQUÍ
            'costo_total_carga': forms.NumberInput(attrs={'class': 'custom-input'}), # CAMBIO AQUÍ
            'es_tanque_lleno': forms.CheckboxInput(attrs={'class': 'form-check-input'}), # Este es diferente
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conductor'].required = False
        self.fields['ruta'].required = False
        self.fields['costo_por_litro'].required = False
        self.fields['costo_total_carga'].required = False
        
        self.fields['conductor'].queryset = User.objects.filter(
            is_active=True, 
            groups__name__in=['Mecánico', 'Supervisor', 'Administrador']
        ).distinct()    


class UsuarioCreacionForm(forms.Form):
    username = forms.CharField(label="Nombre de usuario", max_length=150, widget=forms.TextInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    first_name = forms.CharField(label="Nombre", max_length=150, widget=forms.TextInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    last_name = forms.CharField(label="Apellido", max_length=150, widget=forms.TextInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    email = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.exclude(name='Administrador'),
        label="Rol del Usuario",
        widget=forms.Select(attrs={'class': 'custom-input select2'}) # CAMBIO AQUÍ (y select2)
    )

class UsuarioEdicionForm(forms.Form):
    first_name = forms.CharField(label="Nombre", max_length=150, widget=forms.TextInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    last_name = forms.CharField(label="Apellido", max_length=150, widget=forms.TextInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    email = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={'class': 'custom-input'})) # CAMBIO AQUÍ
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.exclude(name='Administrador'),
        label="Rol del Usuario",
        widget=forms.Select(attrs={'class': 'custom-input select2'}) # CAMBIO AQUÍ (y select2)
    )
