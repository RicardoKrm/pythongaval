from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django_tenants.utils import tenant_context

from .models import Empresa  # Asegúrate de que tu modelo de Tenant se llame Empresa

@receiver(post_save, sender=Empresa)
def crear_grupos_para_nuevo_tenant(sender, instance, created, **kwargs):
    """
    Se ejecuta automáticamente después de que un nuevo tenant (Empresa) es guardado.
    Si el tenant es nuevo (created=True), crea los grupos de roles por defecto.
    """
    if created:
        # Usamos tenant_context para asegurarnos de que estamos operando
        # dentro del schema de la base de datos del nuevo tenant.
        with tenant_context(instance):
            # Lista de roles que queremos crear
            nombres_de_grupos = ['Gerente', 'Administrador', 'Supervisor', 'Mecánico']
            
            for nombre_grupo in nombres_de_grupos:
                # get_or_create: crea el grupo si no existe. 
                # Esto previene errores si por alguna razón ya existiera.
                Group.objects.get_or_create(name=nombre_grupo)
            
            print(f"Grupos por defecto creados para el tenant: {instance.schema_name}")