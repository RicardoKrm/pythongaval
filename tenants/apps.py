from django.apps import AppConfig

class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenants'

    # === INICIO DEL BLOQUE A AÑADIR ===
    def ready(self):
        """
        Este método se ejecuta cuando la aplicación está lista.
        Es el lugar recomendado para importar los signals.
        """
        import tenants.signals  # Importa nuestro archivo de signals para que se conecten
    # === FIN DEL BLOQUE A AÑADIR ===