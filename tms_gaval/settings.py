from pathlib import Path
import locale

# Configuración de localización para el idioma español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252') # Alternativa para Windows
    except locale.Error:
        print("Advertencia: No se pudo establecer la localización en español. Las fechas pueden aparecer en inglés.")


BASE_DIR = Path(__file__).resolve().parent.parent

# ¡IMPORTANTE! Cambia esto en producción a un valor secreto y único.
SECRET_KEY = 'django-insecure-tu-secret-key-aqui'

# ¡IMPORTANTE! Cambia esto a False en producción.
DEBUG = True

ALLOWED_HOSTS = ['*']


# --- CONFIGURACIÓN DE APLICACIONES ---

SHARED_APPS = [
    'django_tenants',  # Debe ser la primera
    'tenants',         # Tu app para los modelos de tenant y dominio

    # Apps de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

TENANT_APPS = [
    # Apps de Django que se usan por tenant
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    
    # Tus apps específicas por tenant
    'flota',
    'cuentas',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]


# --- MIDDLEWARE ---

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware', # Debe estar al principio
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# --- URLS Y TENANTS ---

ROOT_URLCONF = 'tms_gaval.urls' # Ajusta 'tms_gaval' al nombre de tu carpeta de proyecto si es diferente

TENANT_MODEL = "tenants.Empresa"
TENANT_DOMAIN_MODEL = "tenants.Domain"


# --- BASE DE DATOS ---

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': 'tms_gaval_db',
        'USER': 'tms_user',
        'PASSWORD': 'karma627',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)


# --- PLANTILLAS (TEMPLATES) ---

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                'flota.context_processors.notificaciones_processor',
            ],
        },
    },
]


# --- INTERNACIONALIZACIÓN ---

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True


# --- ARCHIVOS ESTÁTICOS ---

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']


# --- OTROS SETTINGS ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'

# === INICIO DEL CAMBIO IMPORTANTE ===
# Ahora redirigimos a una vista especial que decidirá a dónde enviar al usuario.
LOGIN_REDIRECT_URL = 'dashboard'
# === FIN DEL CAMBIO IMPORTANTE ===

LOGOUT_REDIRECT_URL = 'login'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]