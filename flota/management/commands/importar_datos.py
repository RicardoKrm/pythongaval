# flota/management/commands/importar_datos.py (Versión 4 - Completa con Pautas)

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tenants.models import Empresa
from flota.models import Vehiculo, ModeloVehiculo, TipoFalla, PautaMantenimiento

# Configuración de los archivos
VEHICULOS_FILE = 'data/PROGRAMA DE MANT2 (1).xlsx'
FALLAS_FILE = 'data/DIAGRAMA DE PARETO - FALLAS MANTENCIÓN.xlsx'

class Command(BaseCommand):
    help = 'Importa datos desde archivos Excel a un tenant específico.'

    def add_arguments(self, parser):
        parser.add_argument('schema_name', type=str, help='El schema_name del tenant al que se importarán los datos.')

    @transaction.atomic
    def handle(self, *args, **options):
        schema_name = options['schema_name']
        
        try:
            tenant = Empresa.objects.get(schema_name=schema_name)
        except Empresa.DoesNotExist:
            raise CommandError(f'El tenant con schema_name="{schema_name}" no existe.')

        # Establecemos el contexto del tenant
        with tenant:
            self.stdout.write(f"Iniciando importación para el tenant: {tenant.nombre}")
            
            self._importar_modelos_y_vehiculos()
            self._importar_tipos_falla()
            self._importar_pautas()

        self.stdout.write(self.style.SUCCESS('¡Importación completada con éxito!'))

    def _importar_modelos_y_vehiculos(self):
        self.stdout.write("--- Importando Modelos de Vehículo y Vehículos ---")
        try:
            df = pd.read_excel(VEHICULOS_FILE, sheet_name=0, header=1)
            df.columns = df.columns.str.strip()
        except FileNotFoundError:
            raise CommandError(f"Archivo no encontrado: {VEHICULOS_FILE}")

        df = df.dropna(subset=['N° INT.'])

        for _, row in df.iterrows():
            try:
                modelo_nombre = str(row['MODELO']).strip()
                marca = str(row['MARCA']).strip()
                tipo_veh = str(row['TIPO VEH.']).strip()
                
                modelo, created = ModeloVehiculo.objects.get_or_create(
                    nombre=modelo_nombre,
                    defaults={'marca': marca, 'tipo': tipo_veh}
                )
                if created: self.stdout.write(f"  - Modelo Creado: {modelo}")

                num_interno = str(int(row['N° INT.'])).strip()
                vehiculo, created = Vehiculo.objects.update_or_create(
                    numero_interno=num_interno,
                    defaults={
                        'patente': str(row.get('PPU', '')).strip(),
                        'modelo': modelo,
                        'kilometraje_actual': int(row['KM ACTUAL']),
                        'chasis': str(row.get('CHASIS', '')).strip(),
                        'motor': str(row.get('MOTOR', '')).strip()
                    }
                )
            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Omitiendo fila de vehículo por datos incompletos o incorrectos: {e}"))
        
        self.stdout.write(self.style.SUCCESS("Modelos y Vehículos importados."))

    def _importar_tipos_falla(self):
        self.stdout.write("--- Importando Tipos de Falla ---")
        try:
            df = pd.read_excel(FALLAS_FILE, sheet_name=0, header=None, skiprows=7)
            df.columns = [
                'Numero', 'Criticidad', 'Causa', 'Descripcion', 
                'TFS_min', 'Frec_Relativa', 'Frec_Absoluta', 'Punto_Medicion'
            ]
        except FileNotFoundError:
            raise CommandError(f"Archivo no encontrado: {FALLAS_FILE}")
        except Exception as e:
            raise CommandError(f"Error leyendo el archivo Excel de fallas: {e}")

        df = df.dropna(subset=['Descripcion'])

        for _, row in df.iterrows():
            try:
                criticidad_map = {'ALTO': 'ALTA', 'MEDIO': 'MEDIA', 'LEVE': 'BAJA'}
                causa_map = {'MECÁNICA': 'MECANICA', 'ELÉCTRICA': 'ELECTRICA', 'OPERACIÓN': 'OPERACION'}
                
                descripcion = str(row['Descripcion']).strip()
                criticidad_str = str(row.get('Criticidad', 'MEDIA')).strip().upper()
                causa_str = str(row.get('Causa', 'MECANICA')).strip().upper()

                TipoFalla.objects.get_or_create(
                    descripcion=descripcion,
                    defaults={
                        'criticidad': criticidad_map.get(criticidad_str, 'MEDIA'),
                        'causa': causa_map.get(causa_str, 'MECANICA')
                    }
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error importando falla: {row.get('Descripcion', 'N/A')} -> {e}"))

        self.stdout.write(self.style.SUCCESS("Tipos de Falla importados."))

    def _importar_pautas(self):
        self.stdout.write("--- Importando Pautas de Mantenimiento ---")
        try:
            df = pd.read_excel(VEHICULOS_FILE, sheet_name=0, header=1)
            df.columns = df.columns.str.strip()
        except FileNotFoundError:
            raise CommandError(f"Archivo no encontrado: {VEHICULOS_FILE}")

        # Nos enfocamos en las columnas que definen un cronograma
        columnas_requeridas = ['MODELO', 'TIPO MANT.', 'KM PROX. MANT.']
        df_pautas = df.dropna(subset=columnas_requeridas).copy()
        
        # Convertimos la columna de KM a numérico para poder filtrar
        df_pautas['KM PROX. MANT.'] = pd.to_numeric(df_pautas['KM PROX. MANT.'], errors='coerce').fillna(0).astype(int)

        pautas_creadas = 0
        for _, row in df_pautas.iterrows():
            try:
                modelo_nombre = str(row['MODELO']).strip()
                pauta_nombre = str(row['TIPO MANT.']).strip()
                km_pauta = int(row['KM PROX. MANT.'])

                if not modelo_nombre or not pauta_nombre or km_pauta == 0:
                    continue

                # Buscamos el modelo de vehículo que ya debe existir
                modelo_obj = ModeloVehiculo.objects.get(nombre=modelo_nombre)
                
                # Creamos la pauta si no existe para ese modelo y kilometraje
                pauta, created = PautaMantenimiento.objects.get_or_create(
                    modelo_vehiculo=modelo_obj,
                    kilometraje_pauta=km_pauta,
                    defaults={'nombre': pauta_nombre}
                )

                if created:
                    pautas_creadas += 1

            except ModeloVehiculo.DoesNotExist:
                # Este warning es normal si el vehículo no fue creado en el paso anterior
                self.stdout.write(self.style.WARNING(f"  - Omitiendo pauta. Modelo '{modelo_nombre}' no fue encontrado."))
            except ValueError:
                 self.stdout.write(self.style.WARNING(f"  - Omitiendo pauta para '{modelo_nombre}'. Kilometraje inválido: '{row['KM PROX. MANT.']}'"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - Error inesperado procesando pauta para '{modelo_nombre}': {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Se crearon {pautas_creadas} pautas de mantenimiento nuevas."))
        