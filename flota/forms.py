from django import forms
from .models import OrdenDeTrabajo, Tarea, DetalleInsumoOT, Insumo, BitacoraDiaria

class OrdenDeTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['vehiculo', 'tipo', 'formato', 'kilometraje_apertura', 'observacion_inicial']

class AddTareaToOTForm(forms.ModelForm):
    tarea = forms.ModelChoiceField(queryset=Tarea.objects.all(), label="Seleccionar Tarea")
    class Meta:
        model = OrdenDeTrabajo
        fields = ['tarea']

class AddInsumoToOTForm(forms.ModelForm):
    class Meta:
        model = DetalleInsumoOT
        fields = ['insumo', 'cantidad']

class CambiarEstadoOTForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['estado']

class BitacoraDiariaForm(forms.ModelForm):
    class Meta:
        model = BitacoraDiaria
        fields = '__all__'
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
        }

class CargaMasivaForm(forms.Form):
    archivo_vehiculos = forms.FileField(label="Archivo de Flota (Vehículos)", required=False)
    archivo_pautas = forms.FileField(label="Archivo de Pautas de Mantenimiento", required=False)

class CerrarOtMecanicoForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['motivo_pendiente']
        widgets = {
            'motivo_pendiente': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe el trabajo realizado o por qué queda pendiente...'}),
        }

# --- NUEVO FORMULARIO PARA ASIGNAR PERSONAL ---
class AsignarPersonalOTForm(forms.ModelForm):
    class Meta:
        model = OrdenDeTrabajo
        fields = ['responsable', 'personal_asignado']
        widgets = {
            'personal_asignado': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        # Filtra para mostrar solo usuarios que tienen un perfil de Personal
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
            # Si el responsable está en la lista de ayudantes, lo eliminamos automáticamente
            # en lugar de dar un error, lo cual es más amigable para el usuario.
            ayudantes_limpios = ayudantes.exclude(pk=responsable.pk)
            cleaned_data['personal_asignado'] = ayudantes_limpios
        
        return cleaned_data