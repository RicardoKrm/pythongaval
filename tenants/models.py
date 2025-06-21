# tenants/models.py
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Empresa(TenantMixin):
    nombre = models.CharField(max_length=100)
    razon_social = models.CharField(max_length=200, blank=True, null=True)
    creado_en = models.DateField(auto_now_add=True)
    auto_create_schema = True

    def __str__(self):
        return self.nombre

class Domain(DomainMixin):
    # Aunque no usaremos subdominios, la librería necesita este modelo.
    # El dominio aquí será 'localhost' para el tenant público.
    pass