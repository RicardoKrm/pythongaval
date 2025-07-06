from django.contrib import admin
from .models import ModeloVehiculo, NormaEuro, Proveedor, Tarea # Importa los modelos que quieras gestionar

# --- Registrando ModeloVehiculo con personalización ---
@admin.register(ModeloVehiculo)
class ModeloVehiculoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'tipo', 'rendimiento_optimo_kml', 'rendimiento_regular_kml')
    list_filter = ('marca', 'tipo')
    search_fields = ('nombre', 'marca')
    # Hacemos que los nuevos campos de rendimiento sean editables directamente en la lista
    list_editable = ('rendimiento_optimo_kml', 'rendimiento_regular_kml')

# --- Registrando otros modelos de catálogo (opcional pero recomendado) ---
@admin.register(NormaEuro)
class NormaEuroAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email')
    search_fields = ('nombre',)

@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'tiempo_estandar_minutos', 'costo_base')
    search_fields = ('descripcion',)
    list_editable = ('tiempo_estandar_minutos', 'costo_base')


# Puedes seguir registrando otros modelos aquí si lo necesitas
# Ejemplo:
# from .models import Vehiculo
# admin.site.register(Vehiculo)