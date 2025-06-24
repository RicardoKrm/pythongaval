from django import forms
from .models import OrdenDeTrabajo, Tarea, DetalleInsumoOT, Insumo, BitacoraDiaria

class OrdenDeTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['vehiculo', 'tipo', 'formato', 'kilometraje_apertura', 'observacion_inicial']

class CambiarEstadoOTForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['estado']

class BitacoraDiariaForm(forms.ModelForm):
    class Meta:
        model = BitacoraDiaria
        fields = '__all__'
        widgets = { 'fecha': forms.DateInput(attrs={'type': 'date'}), }

class CargaMasivaForm(forms.Form):
    archivo_vehiculos = forms.FileField(label="Archivo de Flota (Vehículos)", required=False)
    archivo_pautas = forms.FileField(label="Archivo de Pautas de Mantenimiento", required=False)

class CerrarOtMecanicoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['motivo_pendiente']
        widgets = { 'motivo_pendiente': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe el trabajo realizado...'}), }

class AsignarPersonalOTForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['responsable', 'personal_asignado']
        widgets = { 'personal_asignado': forms.CheckboxSelectMultiple, }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        usuarios_con_perfil = User.objects.filter(personal__isnull=False)
        self.fields['responsable'].queryset = usuarios_con_perfil
        self.fields['responsable'].label = "Responsable Principal"
        self.fields['personal_asignado'].queryset = usuarios_con_perfil
        self.fields['personal_asignado'].label = "Equipo de Ayudantes"
    def clean(self):
        cleaned_data = super().clean()
        responsable = cleaned_data.get('responsable')
        ayudantes = cleaned_data.get('personal_asignado')
        if responsable and ayudantes and responsable in ayudantes:
            ayudantes_limpios = ayudantes.exclude(pk=responsable.pk)
            cleaned_data['personal_asignado'] = ayudantes_limpios
        return cleaned_data

# === FORMULARIOS PARA ENTRADA MANUAL (LOS QUE FALTABAN) ===
class ManualTareaForm(forms.Form):
    descripcion = forms.CharField(label="Descripción de la Tarea", widget=forms.TextInput(attrs={'placeholder': 'Ej: Cambiar aceite motor'}))
    horas_hombre = forms.DecimalField(label="Horas Hombre", initial=1.0)
    costo_base = forms.DecimalField(label="Costo Tarea", initial=0)

class ManualInsumoForm(forms.Form):
    nombre = forms.CharField(label="Nombre del Insumo", widget=forms.TextInput(attrs={'placeholder': 'Ej: Filtro de aceite'}))
    cantidad = forms.DecimalField(label="Cantidad", initial=1)
    precio_unitario = forms.DecimalField(label="Precio Unitario ($)")