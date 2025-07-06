# flota/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Sum, F, Q # Asegúrate de que Sum, F y Q estén aquí
from django.db.models import Avg


# ==============================================================================
#                      MODELOS DE CATÁLOGO Y SOPORTE
# ==============================================================================

class Proveedor(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    rut = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self): return self.nombre

# Reemplaza la clase ModeloVehiculo completa en flota/models.py

class ModeloVehiculo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    marca = models.CharField(max_length=50)
    tipo = models.CharField(max_length=50, help_text="Ej: Bus, Camión, Camioneta")

    # === INICIO DE LOS NUEVOS CAMPOS ===
    rendimiento_optimo_kml = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.0,
        verbose_name="Rendimiento Óptimo (Km/L)",
        help_text="Rendimiento en Km/L a partir del cual se considera 'ÓPTIMO' (verde)."
    )
    rendimiento_regular_kml = models.DecimalField(
        max_digits=5, decimal_places=2, default=4.0,
        verbose_name="Rendimiento Regular (Km/L)",
        help_text="Rendimiento en Km/L a partir del cual se considera 'REGULAR' (amarillo)."
    )
    # Nota: Cualquier valor por debajo de 'Regular' se considerará 'DEFICIENTE' (rojo).
    # === FIN DE LOS NUEVOS CAMPOS ===

    def __str__(self):
        return f"{self.marca} {self.nombre}"

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
    razon_social = models.CharField(max_length=255, blank=True, null=True, help_text="Razón social o propietario del vehículo")

    def __str__(self):
        patente_str = self.patente or "S/P"
        return f"{self.numero_interno} - {self.modelo.marca} {self.modelo.nombre} ({patente_str})"

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

# Reemplaza la clase ConfiguracionEmpresa completa en flota/models.py

class ConfiguracionEmpresa(models.Model):
    porcentaje_alerta_mantenimiento = models.PositiveIntegerField(
        default=25,
        help_text="Porcentaje del intervalo de KM para activar la alerta 'PRÓXIMO'. Ej: 25."
    )

    # === INICIO DEL NUEVO CAMPO ===
    horas_laborales_mes_por_persona = models.PositiveIntegerField(
        default=160, # Basado en una jornada de 40 horas semanales (40*4)
        verbose_name="Horas Laborales Base por Mes",
        help_text="Número de horas de trabajo estándar que una persona tiene disponibles en un mes. Se usa para calcular la capacidad del equipo."
    )
    # === FIN DEL NUEVO CAMPO ===

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
class Repuesto(models.Model):
    CALIDAD_CHOICES = [
        ('ORIGINAL', 'Original'), 
        ('OEM', 'Alternativo OEM'), # Fabricante de Equipo Original
        ('GENERICO', 'Alternativo Genérico'),
    ]

    nombre = models.CharField(max_length=255, help_text="Nombre descriptivo del repuesto (ej: Filtro de Aceite Motor OM906)")
    numero_parte = models.CharField(max_length=100, help_text="Número de parte o SKU del fabricante")
    calidad = models.CharField(max_length=20, choices=CALIDAD_CHOICES, default='GENERICO')
    
    stock_actual = models.PositiveIntegerField(default=0, verbose_name="Stock Actual")
    stock_minimo = models.PositiveIntegerField(default=1, verbose_name="Stock Mínimo de Alerta")
    
    ubicacion = models.CharField(max_length=100, blank=True, null=True, help_text="Ubicación en bodega (ej: Estante A, Casillero 3)")
    proveedor_habitual = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    
    # NUEVO CAMPO: Precio Unitario del Repuesto para cálculo de costos
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Precio Unitario") # <--- AÑADIR ESTA LÍNEA

    class Meta:
        verbose_name = "Repuesto"
        verbose_name_plural = "Repuestos"
        # Asegura que no puedas tener el mismo número de parte con la misma calidad dos veces
        unique_together = ('numero_parte', 'calidad')

    def __str__(self):
        return f"{self.nombre} ({self.numero_parte}) - {self.get_calidad_display()}"

class MovimientoStock(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ('ENTRADA', 'Entrada (Compra/Recepción)'),
        ('SALIDA_OT', 'Salida por OT'),
        ('AJUSTE_POSITIVO', 'Ajuste de Inventario (Suma)'),
        ('AJUSTE_NEGATIVO', 'Ajuste de Inventario (Resta)'),
    ]

    repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO_CHOICES)
    cantidad = models.IntegerField(help_text="Cantidad del movimiento. Positivo para entradas/ajustes+, negativo para salidas/ajustes-.")
    
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    usuario_responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    orden_de_trabajo = models.ForeignKey('OrdenDeTrabajo', on_delete=models.SET_NULL, null=True, blank=True, help_text="OT asociada a la salida de stock")
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.get_tipo_movimiento_display()}: {self.cantidad} x {self.repuesto.nombre}"

    def save(self, *args, **kwargs):
        # Lógica para actualizar el stock_actual del Repuesto al guardar un movimiento
        # Usamos una transacción para asegurar la consistencia de los datos
        with transaction.atomic():
            # Si el movimiento ya existe (es una actualización), primero revertimos su efecto
            if self.pk:
                movimiento_anterior = MovimientoStock.objects.get(pk=self.pk)
                self.repuesto.stock_actual -= movimiento_anterior.cantidad
            
            # Aplicamos el nuevo efecto del movimiento
            self.repuesto.stock_actual += self.cantidad
            self.repuesto.save()
            
            # Guardamos el movimiento de stock
            super().save(*args, **kwargs)

# ==============================================================================
#                MODELOS DE PAUTAS, TAREAS Y SUS RELACIONES
# ==============================================================================

class RepuestoRequeridoPorTarea(models.Model):
    tarea = models.ForeignKey('Tarea', on_delete=models.CASCADE)
    repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE)
    cantidad_requerida = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('tarea', 'repuesto')

    def __str__(self):
        return f"{self.cantidad_requerida} x {self.repuesto.nombre} para la tarea '{self.tarea.descripcion}'"

# Reemplaza la clase Tarea completa en flota/models.py

class Tarea(models.Model):
    descripcion = models.CharField(max_length=255, unique=True)
    
    # === CAMBIO PRINCIPAL AQUÍ ===
    # Renombramos 'horas_hombre' a 'tiempo_estandar_minutos' para mayor claridad y precisión.
    # Guardaremos el tiempo en minutos para evitar problemas con decimales.
    tiempo_estandar_minutos = models.PositiveIntegerField(
        default=60,
        help_text="Tiempo estándar para completar esta tarea, en minutos."
    )
    # === FIN DEL CAMBIO ===

    costo_base = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo base de mano de obra para esta tarea, sin incluir repuestos.")
    repuestos_requeridos = models.ManyToManyField(Repuesto, through=RepuestoRequeridoPorTarea, blank=True, related_name='tareas_que_lo_requieren')

    def __str__(self):
        return self.descripcion

class PautaMantenimiento(models.Model):
    nombre = models.CharField(max_length=100)
    modelo_vehiculo = models.ForeignKey(ModeloVehiculo, on_delete=models.CASCADE, related_name='pautas')
    kilometraje_pauta = models.PositiveIntegerField()
    tareas = models.ManyToManyField(Tarea, blank=True)
    archivo_pdf = models.FileField(upload_to='pautas/', blank=True, null=True)
    intervalo_km = models.PositiveIntegerField(default=10000, help_text="Intervalo en kilómetros para esta pauta (ej. 10000, 20000)")

    def __str__(self): return f"{self.nombre} ({self.modelo_vehiculo.nombre} - {self.kilometraje_pauta} KM)"

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
    horas_extra_autorizadas = models.BooleanField(
        default=False,
        help_text="Indica si un supervisor autorizó trabajar fuera del tiempo estándar o del horario laboral."
    )
    personal_asignado = models.ManyToManyField(User, related_name='ots_asignadas', blank=True)

    def save(self, *args, **kwargs):
        if not self.folio and not self.pk:
            last_ot = OrdenDeTrabajo.objects.all().order_by('id').last()
            new_id = (last_ot.id + 1) if last_ot else 1
            self.folio = f'OT-{new_id:04d}'

        original_estado = None
        if self.pk:
            try:
                original_estado = OrdenDeTrabajo.objects.get(pk=self.pk).estado
            except OrdenDeTrabajo.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.estado == 'FINALIZADA' and original_estado != 'FINALIZADA':
            if self.kilometraje_cierre and self.kilometraje_cierre > 0:
                if self.vehiculo.kilometraje_actual < self.kilometraje_cierre:
                    self.vehiculo.kilometraje_actual = self.kilometraje_cierre
                    self.vehiculo.save(update_fields=['kilometraje_actual'])

        costo_insumos_actual = self.detalles_insumos_ot.filter(repuesto_inventario__isnull=False).aggregate(
            total=Sum(F('cantidad') * F('repuesto_inventario__precio_unitario'), output_field=models.DecimalField())
        )['total'] or 0.00
        costo_insumos_manuales = self.detalles_insumos_ot.filter(insumo__isnull=False).aggregate(
            total=Sum(F('cantidad') * F('insumo__precio_unitario'), output_field=models.DecimalField())
        )['total'] or 0.00
        costo_tareas_actual = self.tareas_realizadas.aggregate(total=Sum('costo_base'))['total'] or 0.00
        nuevo_costo_total = costo_insumos_actual + costo_insumos_manuales + costo_tareas_actual

        if self.costo_total != nuevo_costo_total:
            self.costo_total = nuevo_costo_total
            OrdenDeTrabajo.objects.filter(pk=self.pk).update(costo_total=self.costo_total)

    def __str__(self):
        return f"OT {self.folio or self.pk} - {self.vehiculo.numero_interno}"

    def has_all_parts_available(self):
        required_parts_data = RepuestoRequeridoPorTarea.objects.filter(
            tarea__in=self.tareas_realizadas.all()
        ).values('repuesto_id', 'repuesto__stock_actual').annotate(
            total_required_for_ot=Sum('cantidad_requerida')
        )
        if not required_parts_data.exists():
            return True
        for item in required_parts_data:
            if item['repuesto__stock_actual'] < item['total_required_for_ot']:
                return False
        return True


class DetalleInsumoOT(models.Model):
    orden_de_trabajo = models.ForeignKey(OrdenDeTrabajo, on_delete=models.CASCADE, related_name='detalles_insumos_ot') # <--- AÑADIR related_name
    
    # Campo para vincular directamente a un Repuesto del inventario (consumido en la OT)
    repuesto_inventario = models.ForeignKey(Repuesto, on_delete=models.SET_NULL, null=True, blank=True, related_name='detalles_ot_asociados_consumo') # <--- AÑADIR ESTA LÍNEA
    
    # Campo para insumos genéricos que no están en el inventario de Repuestos (añadidos manualmente)
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, null=True, blank=True) # <--- MODIFICAR: Añadir null=True, blank=True
    
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        # Para asegurar que SIEMPRE haya un repuesto_inventario O un insumo, pero no ambos
        constraints = [
            models.CheckConstraint(
                check=Q(repuesto_inventario__isnull=False, insumo__isnull=True) |
                      Q(repuesto_inventario__isnull=True, insumo__isnull=False),
                name='one_of_repuesto_or_insumo_not_both_v2' # <--- AÑADIR ESTA RESTRICCIÓN
            )
        ]
        # Si quieres que un repuesto de inventario solo pueda ser añadido una vez por OT:
        # unique_together = ('orden_de_trabajo', 'repuesto_inventario',)
        # PERO CUIDADO: esto puede causar problemas si `repuesto_inventario` es NULL y se combina con `insumo`.
        # Si la adición de stock múltiple ya se maneja en la vista, es mejor omitirlo aquí.

    def __str__(self):
        if self.repuesto_inventario:
            return f"{self.cantidad} x {self.repuesto_inventario.nombre} (Inv.) en OT {self.orden_de_trabajo.folio or self.orden_de_trabajo.pk}"
        elif self.insumo:
            return f"{self.cantidad} x {self.insumo.nombre} (Manual) en OT {self.orden_de_trabajo.folio or self.orden_de_trabajo.pk}"
        return f"{self.cantidad} x Insumo Desconocido en OT {self.orden_de_trabajo.folio or self.orden_de_trabajo.pk}"

    def save(self, *args, **kwargs):
        # Asegurarse de que solo uno de los dos campos (repuesto_inventario o insumo) esté lleno
        if self.repuesto_inventario and self.insumo:
            raise ValueError("Un DetalleInsumoOT no puede tener un repuesto de inventario y un insumo manual al mismo tiempo.")
        if not self.repuesto_inventario and not self.insumo:
            raise ValueError("Un DetalleInsumoOT debe tener un repuesto de inventario o un insumo manual.")
        super().save(*args, **kwargs)

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
    
# pégalo al final de tu archivo flota/models.py

# ==============================================================================
#                      MODELOS DE CONTROL DE COMBUSTIBLE
# ==============================================================================

class Ruta(models.Model):
    TOPOGRAFIA_CHOICES = [
        ('PLANO', 'Plano'),
        ('MIXTO', 'Mixto'),
        ('MONTANOSO', 'Montañoso'),
    ]
    PAVIMENTO_CHOICES = [
        ('ASFALTO', 'Asfalto'),
        ('TIERRA', 'Tierra'),
        ('MIXTO', 'Mixto'),
    ]
    
    nombre = models.CharField(max_length=255, unique=True, help_text="Ej: Calama - Antofagasta")
    distancia_km = models.DecimalField(max_digits=10, decimal_places=2, help_text="Distancia estándar de la ruta en kilómetros")
    topografia = models.CharField(max_length=20, choices=TOPOGRAFIA_CHOICES, default='MIXTO')
    tipo_pavimento = models.CharField(max_length=20, choices=PAVIMENTO_CHOICES, default='ASFALTO')
    
    class Meta:
        verbose_name = "Ruta"
        verbose_name_plural = "Rutas"

    def __str__(self):
        return self.nombre

class CondicionAmbiental(models.Model):
    CLIMA_CHOICES = [
        ('DESPEJADO', 'Despejado'),
        ('LLUVIA', 'Lluvia'),
        ('VIENTO', 'Viento Fuerte'),
        ('NIEVE', 'Nieve'),
    ]
    TRAFICO_CHOICES = [
        ('BAJO', 'Bajo'),
        ('MODERADO', 'Moderado'),
        ('ALTO', 'Alto'),
    ]
    
    fecha_medicion = models.DateField()
    temperatura_celsius = models.IntegerField(default=15)
    condicion_climatica = models.CharField(max_length=20, choices=CLIMA_CHOICES, default='DESPEJADO')
    nivel_trafico = models.CharField(max_length=20, choices=TRAFICO_CHOICES, default='BAJO')

    class Meta:
        verbose_name = "Condición Ambiental"
        verbose_name_plural = "Condiciones Ambientales"
    
    def __str__(self):
        return f"{self.fecha_medicion}: {self.temperatura_celsius}°C, {self.get_condicion_climatica_display()}"


class CargaCombustible(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='cargas_combustible')
    conductor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargas_realizadas')
    ruta = models.ForeignKey(Ruta, on_delete=models.SET_NULL, null=True, blank=True)
    condicion_ambiental = models.ForeignKey(CondicionAmbiental, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha_carga = models.DateTimeField(default=timezone.now)
    kilometraje_en_carga = models.PositiveIntegerField(help_text="Odómetro del vehículo al momento de la carga")
    litros_cargados = models.DecimalField(max_digits=10, decimal_places=2)
    costo_por_litro = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    costo_total_carga = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    es_tanque_lleno = models.BooleanField(default=True, help_text="Marcar si la carga fue para llenar el tanque")
    rendimiento_calculado_kml = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, 
        verbose_name="Rendimiento del Tramo Anterior (Km/L)",
        help_text="Calculado automáticamente al registrar la siguiente carga."
    )

    class Meta:
        verbose_name = "Carga de Combustible"
        verbose_name_plural = "Cargas de Combustible"
        ordering = ['-fecha_carga']

    def __str__(self):
        return f"Carga de {self.litros_cargados} Lts para {self.vehiculo.numero_interno} el {self.fecha_carga.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        # Primero, guarda la instancia actual para asegurar que tiene un ID.
        # Esto es importante para que la lógica de búsqueda del registro anterior funcione correctamente.
        super().save(*args, **kwargs)

        # Busca el registro de carga inmediatamente anterior para el mismo vehículo.
        # Se excluye el objeto actual (self) de la búsqueda.
        carga_anterior = CargaCombustible.objects.filter(
            vehiculo=self.vehiculo,
            pk__lt=self.pk # Busca registros con un ID menor al actual
        ).order_by('-pk').first() # Ordena por ID descendente y toma el primero
        
        if carga_anterior:
            # Calcula la distancia recorrida desde la última carga
            distancia_recorrida = self.kilometraje_en_carga - carga_anterior.kilometraje_en_carga
            
            # Asegúrate de que los valores son positivos y lógicos para evitar errores
            if distancia_recorrida > 0 and carga_anterior.litros_cargados > 0:
                # Calcula el rendimiento del tramo anterior
                rendimiento = distancia_recorrida / carga_anterior.litros_cargados
                
                # Actualiza el campo de rendimiento en el registro ANTERIOR
                carga_anterior.rendimiento_calculado_kml = rendimiento
                # Usamos update_fields para ser eficientes y evitar recursion infinita de save()
                carga_anterior.save(update_fields=['rendimiento_calculado_kml'])

        # También actualiza el kilometraje del vehículo principal
        if self.vehiculo.kilometraje_actual < self.kilometraje_en_carga:
            self.vehiculo.kilometraje_actual = self.kilometraje_en_carga
            self.vehiculo.save(update_fields=['kilometraje_actual'])

class Notificacion(models.Model):
    """
    Modela una notificación para un usuario específico dentro de la aplicación.
    """
    # El usuario que recibirá la notificación. Si se borra el usuario, se borran sus notificaciones.
    usuario_destino = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notificaciones'
    )
    
    # El contenido de la notificación
    mensaje = models.CharField(
        max_length=255, 
        help_text="El texto que verá el usuario. Ej: 'La OT #123 fue pausada por Juan Pérez.'"
    )
    
    # Un campo para saber si el usuario ya vio la notificación
    leida = models.BooleanField(default=False)
    
    # La URL a la que se redirigirá al usuario si hace clic en la notificación
    url_destino = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="URL a la que se dirige la notificación. Ej: /ot/123/detail/"
    )
    
    # La fecha en que se creó la notificación
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion'] # Muestra las notificaciones más nuevas primero
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"Notificación para {self.usuario_destino.username}: {self.mensaje[:30]}..."