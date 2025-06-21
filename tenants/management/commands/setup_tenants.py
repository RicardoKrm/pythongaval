# tenants/management/commands/setup_tenants.py (Versión 2 - Mejorada)

from django.core.management.base import BaseCommand
from tenants.models import Empresa, Domain

class Command(BaseCommand):
    help = 'Crea o verifica los tenants y dominios iniciales para el desarrollo'

    def handle(self, *args, **options):
        self.stdout.write("--- Iniciando configuración de tenants ---")

        # --- TENANT PÚBLICO ---
        # Usamos get_or_create para crear el tenant solo si no existe
        public_tenant, created = Empresa.objects.get_or_create(
            schema_name='public', 
            defaults={'nombre': 'Administración Global'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Tenant 'public' creado."))
        else:
            self.stdout.write(self.style.WARNING("Tenant 'public' ya existe."))

        # Verificamos y creamos el dominio '127.0.0.1'
        domain1, created = Domain.objects.get_or_create(
            domain='127.0.0.1', 
            defaults={'tenant': public_tenant, 'is_primary': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Dominio '127.0.0.1' creado y asociado."))
        else:
            self.stdout.write(self.style.WARNING("Dominio '127.0.0.1' ya existe."))

        # Verificamos y creamos el dominio 'localhost'
        domain2, created = Domain.objects.get_or_create(
            domain='localhost', 
            defaults={'tenant': public_tenant, 'is_primary': False}
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Dominio 'localhost' creado y asociado."))
        else:
            self.stdout.write(self.style.WARNING("Dominio 'localhost' ya existe."))


        # --- TENANT SANTA ROSA ---
        santarosa_tenant, created = Empresa.objects.get_or_create(
            schema_name='santarosa', 
            defaults={'nombre': 'Santa Rosa Pullman', 'razon_social': 'Transportes Santa Rosa S.A.'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Tenant 'santarosa' creado."))
        else:
            self.stdout.write(self.style.WARNING("Tenant 'santarosa' ya existe."))
        
        # Verificamos y creamos el dominio 'santarosa.localhost'
        domain_sr, created = Domain.objects.get_or_create(
            domain='santarosa.localhost', 
            defaults={'tenant': santarosa_tenant, 'is_primary': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Dominio 'santarosa.localhost' creado y asociado."))
        else:
            self.stdout.write(self.style.WARNING("Dominio 'santarosa.localhost' ya existe."))
        
        self.stdout.write("--- Configuración de tenants finalizada ---")