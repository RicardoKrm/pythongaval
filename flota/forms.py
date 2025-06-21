# flota/forms.py


from django import forms

from .models import (

    OrdenDeTrabajo, Vehiculo, Tarea, Insumo,

    DetalleInsumoOT, BitacoraDiaria

)


class VehiculoChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):

        patente_str = obj.patente or "S/P"

        return f"{obj.numero_interno} - {obj.modelo.marca} {obj.modelo.nombre} ({patente_str})"


class OrdenDeTrabajoForm(forms.ModelForm):

    vehiculo = VehiculoChoiceField(

        queryset=Vehiculo.objects.all().order_by('numero_interno'),

        label="Vehículo",

        widget=forms.Select(attrs={'class': 'form-control'})

    )

    class Meta:

        model = OrdenDeTrabajo

        # Se quita 'folio' porque ahora es automático

        fields = ['vehiculo', 'tipo', 'kilometraje_apertura', 'observacion_inicial', 'tipo_falla']

        widgets = {

            'tipo': forms.Select(attrs={'class': 'form-control'}),

            'kilometraje_apertura': forms.NumberInput(attrs={'class': 'form-control'}),

            'observacion_inicial': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            'tipo_falla': forms.Select(attrs={'class': 'form-control'}),

        }


class AddTareaToOTForm(forms.Form):

    tarea = forms.ModelChoiceField(

        queryset=Tarea.objects.all().order_by('descripcion'),

        label="Seleccionar Tarea a Añadir",

        widget=forms.Select(attrs={'class': 'form-control'})

    )


class AddInsumoToOTForm(forms.ModelForm):

    class Meta:

        model = DetalleInsumoOT

        fields = ['insumo', 'cantidad']

        widgets = {

            'insumo': forms.Select(attrs={'class': 'form-control'}),

            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad utilizada'}),

        }


class CambiarEstadoOTForm(forms.ModelForm):

    class Meta:

        model = OrdenDeTrabajo

        fields = ['estado']

        widgets = {

            'estado': forms.Select(attrs={'class': 'form-control'})

        }


class BitacoraDiariaForm(forms.ModelForm):

    # Definimos los campos explícitamente aquí para controlar el orden

    vehiculo = VehiculoChoiceField(

        queryset=Vehiculo.objects.all().order_by('numero_interno'),

        label="Vehículo",

        widget=forms.Select(attrs={'class': 'form-control'})

    )

    fecha = forms.DateField(

        label="Fecha del Parte",

        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})

    )

    horas_operativas = forms.DecimalField(

        label="Horas Operativas",

        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'value': '0'})

    )

    horas_mantenimiento_prog = forms.DecimalField(

        label="Horas Mant. Programado",

        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'value': '0'})

    )

    horas_falla = forms.DecimalField(

        label="Horas por Falla (No Prog.)",

        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'value': '0'})

    )


    class Meta:

        model = BitacoraDiaria

        # La lista de fields ahora solo confirma los campos del modelo que usamos

        fields = ['vehiculo', 'fecha', 'horas_operativas', 'horas_mantenimiento_prog', 'horas_falla']


class CerrarOtMecanicoForm(forms.ModelForm):

    class Meta:

        model = OrdenDeTrabajo

        fields = ['motivo_pendiente']

        widgets = {

            'motivo_pendiente': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Si dejas la OT pendiente, explica el motivo aquí...'}),

        }


class CargaMasivaForm(forms.Form):

    # Usamos FileField para cada tipo de archivo que permitimos subir.

    # 'required=False' permite al usuario subir solo los archivos que necesite en cada momento.

    archivo_vehiculos = forms.FileField(

        label="Archivo de Vehículos (Excel)",

        required=False,

        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})

    )

    archivo_tareas = forms.FileField(

        label="Archivo de Tareas (Excel)",

        required=False,

        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})

    )

    archivo_insumos = forms.FileField(

        label="Archivo de Insumos (Excel)",

        required=False,

        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})

    )         