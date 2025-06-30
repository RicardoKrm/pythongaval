# flota/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Sum, F, Q # Asegúrate de que Sum, F y Q estén aquí


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

class ConfiguracionEmpresa(models.Model):
    porcentaje_alerta_mantenimiento = models.PositiveIntegerField(
        default=25,
        help_text="Porcentaje del intervalo de KM para activar la alerta 'PRÓXIMO'. Ej: 25."
    )

    def __str__(self): return "Configuración General de la Empresa"

    class Meta:
        verbose_name_plural = "Configuraciones de Empresa"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(ConfiguracionEmpresa, self).save(*args, **kwargs)    
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

# ==============================================================================
#                      MODELOS DE INVENTARIO
# ==============================================================================

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

class Tarea(models.Model):
    descripcion = models.CharField(max_length=255, unique=True)
    horas_hombre = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    costo_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Nueva relación para repuestos requeridos por esta tarea
    repuestos_requeridos = models.ManyToManyField(Repuesto, through=RepuestoRequeridoPorTarea, blank=True, related_name='tareas_que_lo_requieren')

    def __str__(self): return self.descripcion

class PautaMantenimiento(models.Model):
    nombre = models.CharField(max_length=100)
    modelo_vehiculo = models.ForeignKey(ModeloVehiculo, on_delete=models.CASCADE, related_name='pautas')
    kilometraje_pauta = models.PositiveIntegerField()
    tareas = models.ManyToManyField(Tarea, blank=True)
    archivo_pdf = models.FileField(upload_to='pautas/', blank=True, null=True)
    intervalo_km = models.PositiveIntegerField(default=10000, help_text="Intervalo en kilómetros para esta pauta (ej. 10000, 20000)")

    def __str__(self): return f"{self.nombre} ({self.modelo_vehiculo.nombre} - {self.kilometraje_pauta} KM)"

# ==============================================================================
#                      MODELOS PRINCIPALES DE OPERACIÓN
# ==============================================================================

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
    
    # CAMBIO AQUÍ: La relación ManyToMany `insumos_utilizados` se gestionará mejor
    # a través del `related_name` de DetalleInsumoOT, ya no es necesaria aquí.
    # Puedes comentar o eliminar esta línea:
    # insumos_utilizados = models.ManyToManyField(Insumo, through='DetalleInsumoOT', blank=True)
    
    personal_asignado = models.ManyToManyField(User, related_name='ots_asignadas', blank=True)

    # --- MÉTODOS DEL MODELO ---
    def save(self, *args, **kwargs):
        if not self.folio:
            last_ot = OrdenDeTrabajo.objects.all().order_by('id').last()
            new_id = (last_ot.id + 1) if last_ot else 1
            self.folio = f'OT-{new_id:04d}'
        
        # Recalcular el costo total de la OT antes de guardar
        costo_insumos = 0
        # ¡IMPORTANTE! Usamos el nuevo related_name 'detalles_insumos_ot'
        for detalle in self.detalles_insumos_ot.all():
            if detalle.repuesto_inventario: # Si es un repuesto del inventario
                # Asegúrate de que Repuesto.precio_unitario esté definido
                costo_insumos += detalle.cantidad * detalle.repuesto_inventario.precio_unitario
            elif detalle.insumo: # Si es un insumo genérico (no de inventario)
                costo_insumos += detalle.cantidad * detalle.insumo.precio_unitario
        
        costo_tareas = self.tareas_realizadas.aggregate(total=Sum('costo_base'))['total'] or 0
        self.costo_total = costo_insumos + costo_tareas
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OT {self.folio or self.pk} - {self.vehiculo.numero_interno}"

    # --- ¡NUEVO MÉTODO PARA LA DISPONIBILIDAD DE REPUESTOS PLANIFICADOS! ---
    def has_all_parts_available(self):
        """
        Verifica si todos los repuestos *planificados* (requeridos por las tareas asociadas)
        para esta Orden de Trabajo están disponibles en el stock actual.
        """
        # Obtener todas las relaciones RepuestoRequeridoPorTarea para las tareas de esta OT
        # Usamos .values() y .annotate() para agrupar por repuesto y sumar las cantidades requeridas
        required_parts_data = RepuestoRequeridoPorTarea.objects.filter(
            tarea__in=self.tareas_realizadas.all()
        ).values('repuesto__id', 'repuesto__stock_actual').annotate(
            total_required_for_ot=Sum('cantidad_requerida')
        )

        if not required_parts_data.exists():
            # Si la OT no tiene tareas que requieran repuestos, se considera que están disponibles.
            return True

        for item in required_parts_data:
            repuesto_stock = item['repuesto__stock_actual']
            total_required = item['total_required_for_ot']

            if repuesto_stock < total_required:
                return False # En cuanto encuentra un repuesto faltante, retorna False

        return True # Si revisó todos y todos están disponibles, retorna True


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