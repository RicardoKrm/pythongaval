# ==============================================================================
# CREA ESTE ARCHIVO Y PEGA EL CÓDIGO:
# tms_gaval_final/management/commands/update_domains_to_path.py
# ==============================================================================

from django.core.management.base import BaseCommand
from django.db import transaction
from tenants.models import Client, Domain

class Command(BaseCommand):
    """
    Comando de Django para migrar de una arquitectura de subdominios
    a una arquitectura de enrutamiento por path (subcarpetas) en django-tenants.
    """
    help = 'Updates tenant domains from subdomains to a path-based routing structure.'

    def handle(self, *args, **options):
        
        # ----- CONFIGURACIÓN PRINCIPAL -----
        BASE_DOMAIN = 'localhost'
        PUBLIC_SCHEMA_NAME = 'public'
        TENANTS_DATA = {
            'Gaval Transportes': {
                'subdomain_antiguo': 'gaval.localhost',
                'path_nuevo': 'gaval'
            },
            'Santa Rosa Pullman': {
                'subdomain_antiguo': 'santarosa.localhost',
                'path_nuevo': 'santarosa'
            },
        }
        # -------------------------------------

        self.stdout.write(self.style.SUCCESS("====================================================="))
        self.stdout.write(self.style.SUCCESS("=== Iniciando migración a enrutamiento por PATH   ==="))
        self.stdout.write(self.style.SUCCESS("====================================================="))

        try:
            with transaction.atomic():
                # --- PASO 1: Configurar el Tenant Público ---
                self.stdout.write(f"\nConfigurando tenant público ('{PUBLIC_SCHEMA_NAME}')...")
                try:
                    public_tenant = Client.objects.get(schema_name=PUBLIC_SCHEMA_NAME)
                    
                    # Eliminar dominios del tenant público que no sean el base
                    public_tenant.domains.exclude(domain=BASE_DOMAIN).delete()
                    
                    # Crear/actualizar el dominio para el tenant público
                    domain_public, created = Domain.objects.get_or_create(
                        tenant=public_tenant,
                        domain=BASE_DOMAIN,
                        defaults={'is_primary': True, 'folder': None} # folder es NULL o ''
                    )
                    
                    if not created:
                        domain_public.folder = None
                        domain_public.is_primary = True
                        domain_public.save()
                        
                    self.stdout.write(self.style.SUCCESS(f"-> OK: Tenant público responderá en http://{BASE_DOMAIN}:8000/"))

                except Client.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"FATAL: No se encontró el tenant público con schema_name='{PUBLIC_SCHEMA_NAME}'. Abortando."))
                    raise

                # --- PASO 2: Migrar los Tenants de Clientes ---
                self.stdout.write("\nMigrando tenants de clientes...")
                for tenant_name, data in TENANTS_DATA.items():
                    subdomain_antiguo = data['subdomain_antiguo']
                    path_nuevo = data['path_nuevo']
                    
                    self.stdout.write(f"Procesando tenant: '{tenant_name}'...")
                    
                    try:
                        tenant = Client.objects.get(name=tenant_name)
                        
                        # Eliminar el dominio antiguo
                        tenant.domains.filter(domain=subdomain_antiguo).delete()
                        
                        # Crear/actualizar el nuevo dominio basado en path
                        domain, created = Domain.objects.get_or_create(
                            tenant=tenant,
                            domain=BASE_DOMAIN,
                            folder=path_nuevo,
                            defaults={'is_primary': False}
                        )
                        
                        if not created and domain.is_primary:
                            domain.is_primary = False
                            domain.save()
                        
                        self.stdout.write(self.style.SUCCESS(f"  -> OK: Tenant '{tenant_name}' responderá en http://{BASE_DOMAIN}:8000/{path_nuevo}/"))

                    except Client.DoesNotExist:
                        self.stderr.write(self.style.WARNING(f"  - AVISO: No se encontró el tenant '{tenant_name}'. Saltando..."))
                        continue

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\nHa ocurrido un error. No se realizaron cambios. Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("\n====================================================="))
        self.stdout.write(self.style.SUCCESS("=== Migración completada con éxito.               ==="))
        self.stdout.write(self.style.SUCCESS("====================================================="))