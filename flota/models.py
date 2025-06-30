from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.auth.models import User


# --- Catálogos Fundamentales ---

class Proveedor(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    rut = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    def __str__(self): return self.nombre

class ModeloVehiculo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    marca = models.CharField(max_length=50)
    tipo = models.CharField(max_length=50, help_text="Ej: Bus, Camión, Camioneta")
    def __str__(self): return f"{self.marca} {self.nombre}"

class NormaEuro(models.Model):
    nombre = models.CharField(max_length=20, unique=True, help_text="Ej: EURO V, EURO VI")
    def __str__(self): return self.nombre

class Vehiculo(models.Model):
    numero_interno = models.CharField(max_length=50, unique=True)
    patente = models.CharField(max_length=10, unique=True, blank=True, null=True)
    modelo = models.ForeignKey(ModeloVehiculo, on_delete=models.PROTECT, related_name='vehiculos')
    kilometraje_actual = models.PositiveIntegerField(default=0)
    chasis = models.CharField(max_length=100, blank=True, null=True)
    motor = models.CharField(max_length=100, blank=True, null=True)
    fecha_actualizacion_km = models.DateTimeField(auto_now=True)
    aplicacion = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Faena, Carretera, Interurbano")
    norma_euro = models.ForeignKey(NormaEuro, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehiculos')
    def __str__(self):
        patente_str = self.patente or "S/P"
        return f"{self.numero_interno} - {self.modelo.marca} {self.modelo.nombre} ({patente_str})"

class Tarea(models.Model):
    descripcion = models.CharField(max_length=255, unique=True)
    horas_hombre = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    costo_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    def __str__(self): return self.descripcion

class Insumo(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    categoria = models.CharField(max_length=100, default="General")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    def __str__(self): return self.nombre

class Personal(models.Model):
    ROL_CHOICES = [('ADMINISTRADOR', 'Administrador'), ('SUPERVISOR', 'Supervisor'), ('MECANICO', 'Mecánico'), ('ASISTENTE', 'Asistente')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="Usuario de Django asociado para el inicio de sesión. Déjelo en blanco si no necesita login.")
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=20, unique=True)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='MECANICO')
    def __str__(self): return f"{self.nombre} ({self.get_rol_display()})"
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.user:
            try:
                rol_nombre_legible = self.get_rol_display()
                grupo, created = Group.objects.get_or_create(name=rol_nombre_legible)
                self.user.groups.clear()
                self.user.groups.add(grupo)
            except Exception as e: print(f"ADVERTENCIA: No se pudo asignar el grupo '{rol_nombre_legible}' al usuario '{self.user.username}'. Error: {e}")

class TipoFalla(models.Model):
    CRITICIDAD_CHOICES = [('ALTA', 'Alta'), ('MEDIA', 'Media'), ('BAJA', 'Baja')]
    CAUSA_CHOICES = [('MECANICA', 'Mecánica'), ('ELECTRICA', 'Eléctrica'), ('OPERACION', 'Operación')]
    descripcion = models.CharField(max_length=255, unique=True)
    criticidad = models.CharField(max_length=10, choices=CRITICIDAD_CHOICES, default='MEDIA')
    causa = models.CharField(max_length=10, choices=CAUSA_CHOICES, default='MECANICA')
    def __str__(self): return self.descripcion

class PautaMantenimiento(models.Model):
    nombre = models.CharField(max_length=100)
    modelo_vehiculo = models.ForeignKey(ModeloVehiculo, on_delete=models.CASCADE, related_name='pautas')
    kilometraje_pauta = models.PositiveIntegerField()
    tareas = models.ManyToManyField(Tarea, blank=True)
    archivo_pdf = models.FileField(upload_to='pautas/', blank=True, null=True)
    intervalo_km = models.PositiveIntegerField(default=10000, help_text="Intervalo en kilómetros para esta pauta (ej. 10000, 20000)")
    def __str__(self): return f"{self.nombre} ({self.modelo_vehiculo.nombre} - {self.kilometraje_pauta} KM)"

# En flota/models.py

class OrdenDeTrabajo(models.Model):
    # --- CHOICES ---
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('PAUSADA', 'Pausada'),
        ('CERRADA_MECANICO', 'Cerrada por Mecánico'),
        ('FINALIZADA', 'Finalizada'),
    ]
    TIPO_CHOICES = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRECTIVA', 'Correctiva'),
        ('EVALUATIVA', 'Evaluativa'),
    ]
    FORMATO_CHOICES = [
        ('INTERNO', 'Interno'),
        ('EXTERNO', 'Externo'),
    ]
    MOTIVO_PAUSA_CHOICES = [
        ('FALTA_REPUESTO', 'Falta de Repuesto'),
        ('ESPERA_AUTORIZACION', 'Espera de Autorización'),
        ('FALTA_PERSONAL', 'Falta de Personal'),
        ('OTRO', 'Otro'),
    ]
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    
    # --- CAMPOS DEL MODELO ---
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='MEDIA',
        verbose_name="Prioridad"
    )
    folio = models.CharField(max_length=20, unique=True, blank=True, null=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='ordenes_de_trabajo')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    formato = models.CharField(max_length=10, choices=FORMATO_CHOICES, default='INTERNO')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    fecha_programada = models.DateField(null=True, blank=True)
    kilometraje_apertura = models.PositiveIntegerField(null=True, blank=True)
    kilometraje_cierre = models.PositiveIntegerField(null=True, blank=True)
    observacion_inicial = models.TextField(blank=True, null=True)
    costo_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    motivo_pendiente = models.TextField(blank=True, null=True)
    tfs_minutos = models.PositiveIntegerField(default=0, help_text="Tiempo Fuera de Servicio en minutos")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_falla = models.ForeignKey(TipoFalla, on_delete=models.SET_NULL, null=True, blank=True)
    pauta_mantenimiento = models.ForeignKey(PautaMantenimiento, on_delete=models.SET_NULL, null=True, blank=True)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ots_responsable')
    sintomas_reportados = models.TextField(blank=True, null=True)
    diagnostico_evaluacion = models.TextField(blank=True, null=True)
    motivo_pausa = models.CharField(max_length=50, choices=MOTIVO_PAUSA_CHOICES, blank=True, null=True)
    notas_pausa = models.TextField(blank=True, null=True)
    tareas_realizadas = models.ManyToManyField(Tarea, blank=True, related_name='ordenes_de_trabajo')
    insumos_utilizados = models.ManyToManyField(Insumo, through='DetalleInsumoOT', blank=True)
    personal_asignado = models.ManyToManyField(User, related_name='ots_asignadas', blank=True)

    # --- MÉTODOS DEL MODELO ---
    def save(self, *args, **kwargs):
        # SOLUCIÓN 2: INDENTACIÓN CORREGIDA
        if not self.folio:
            last_ot = OrdenDeTrabajo.objects.all().order_by('id').last()
            new_id = (last_ot.id + 1) if last_ot else 1
            self.folio = f'OT-{new_id:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        # SOLUCIÓN 2: INDENTACIÓN CORREGIDA
        return f"OT {self.folio or self.pk} - {self.vehiculo.numero_interno}"

class DetalleInsumoOT(models.Model):
    orden_de_trabajo = models.ForeignKey(OrdenDeTrabajo, on_delete=models.CASCADE)
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self): return f"{self.cantidad} x {self.insumo.nombre} en OT {self.orden_de_trabajo.folio or self.orden_de_trabajo.pk}"

class BitacoraDiaria(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='bitacoras')
    fecha = models.DateField()
    horas_operativas = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    horas_mantenimiento_prog = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    horas_falla = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    class Meta:
        unique_together = ('vehiculo', 'fecha')
        ordering = ['-fecha']
    def __str__(self): return f"Bitácora de {self.vehiculo.numero_interno} para {self.fecha}"

class ConfiguracionEmpresa(models.Model):
    porcentaje_alerta_mantenimiento = models.PositiveIntegerField(
        default=25,
        help_text="Porcentaje del intervalo de KM para activar la alerta 'PRÓXIMO'. Ej: 25."
    )

    def __str__(self):
        return "Configuración General de la Empresa"

    class Meta:
        verbose_name_plural = "Configuraciones de Empresa"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(ConfiguracionEmpresa, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj    
    
class HistorialOT(models.Model):
    """
    Registra cada evento significativo que ocurre en una Orden de Trabajo
    para propósitos de auditoría y trazabilidad.
    """
    TIPO_EVENTO_CHOICES = [
        ('CREACION', 'Creación de OT'),
        ('ASIGNACION', 'Asignación de Personal'),
        ('INICIO', 'Inicio de Tareas'),
        ('PAUSA', 'OT Pausada'),
        ('REANUDACION', 'OT Reanudada'),
        ('CIERRE_MECANICO', 'Cierre por Mecánico'),
        ('FINALIZACION', 'Finalización de OT'),
        ('MODIFICACION', 'Modificación de Datos'),
        ('COMENTARIO', 'Comentario'),
    ]

    orden_de_trabajo = models.ForeignKey(OrdenDeTrabajo, on_delete=models.CASCADE, related_name='historial')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="Usuario que realizó la acción")
    fecha_evento = models.DateTimeField(auto_now_add=True)
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES)
    descripcion = models.TextField(help_text="Detalle del evento. Ej: 'Pausada por falta de repuesto: Filtro de aceite.'")

    class Meta:
        ordering = ['-fecha_evento'] # Muestra los eventos más recientes primero

    def __str__(self):
        user_str = self.usuario.username if self.usuario else "Sistema"
        return f"{self.get_tipo_evento_display()} en OT-{self.orden_de_trabajo.folio} por {user_str}"    