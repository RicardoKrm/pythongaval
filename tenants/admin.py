# tenants/admin.py
from django.contrib import admin
from .models import Empresa, Domain

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'schema_name', 'creado_en')
    search_fields = ('nombre', 'schema_name')

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain',)
    list_filter = ('tenant', 'is_primary')