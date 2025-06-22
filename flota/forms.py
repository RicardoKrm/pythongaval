# flota/forms.py

from django import forms
from .models import (
    OrdenDeTrabajo, Vehiculo, Tarea, Insumo, 
    DetalleInsumoOT, BitacoraDiaria, PautaMantenimiento
)

class VehiculoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        patente_str = obj.patente or "S/P"
        return f"{obj.numero_interno} - {obj.modelo.marca} {obj.modelo.nombre} ({patente_str})"

class OrdenDeTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['vehiculo', 'tipo', 'formato', 'kilometraje_apertura', 'observacion_inicial', 'tipo_falla', 'tfs_minutos']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'formato': forms.Select(attrs={'class': 'form-control'}),
            'kilometraje_apertura': forms.NumberInput(attrs={'class': 'form-control'}),
            'observacion_inicial': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo_falla': forms.Select(attrs={'class': 'form-control'}),
            'tfs_minutos': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class AddTareaToOTForm(forms.Form):
    tarea = forms.ModelChoiceField(queryset=Tarea.objects.all().order_by('descripcion'), label="Seleccionar Tarea a Añadir", widget=forms.Select(attrs={'class': 'form-control'}))

class AddInsumoToOTForm(forms.ModelForm):
    class Meta:
        model = DetalleInsumoOT
        fields = ['insumo', 'cantidad']
        widgets = {'insumo': forms.Select(attrs={'class': 'form-control'}), 'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad utilizada'})}

class CambiarEstadoOTForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['estado']
        widgets = {'estado': forms.Select(attrs={'class': 'form-control'})}

class CerrarOtMecanicoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['motivo_pendiente']
        widgets = {'motivo_pendiente': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Si dejas la OT pendiente, explica el motivo aquí...'})}

class BitacoraDiariaForm(forms.ModelForm):
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    vehiculo = VehiculoChoiceField(queryset=Vehiculo.objects.all().order_by('numero_interno'), label="Vehículo", widget=forms.Select(attrs={'class': 'form-control'}))
    class Meta:
        model = BitacoraDiaria
        fields = ['vehiculo', 'fecha', 'horas_operativas', 'horas_mantenimiento_prog', 'horas_falla']
        widgets = {
            'horas_operativas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'value': '0'}),
            'horas_mantenimiento_prog': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'value': '0'}),
            'horas_falla': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'value': '0'}),
        }

class CargaMasivaForm(forms.Form):
    archivo_vehiculos = forms.FileField(label="Archivo de Vehículos (Excel)", required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    archivo_tareas = forms.FileField(label="Archivo de Tareas (Excel)", required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    archivo_insumos = forms.FileField(label="Archivo de Insumos (Excel)", required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))