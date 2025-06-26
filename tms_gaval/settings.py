from pathlib import Path
import locale
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-tu-secret-key-aqui'
DEBUG = True
ALLOWED_HOSTS = ['*']

SHARED_APPS = [
    'django_tenants',
    'tenants',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
]
TENANT_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    
    'flota',
    'cuentas',
]
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'tms_gaval.urls'
TENANT_MODEL = "tenants.Empresa"
TENANT_DOMAIN_MODEL = "tenants.Domain"
DATABASES = {'default': {'ENGINE': 'django_tenants.postgresql_backend', 'NAME': 'tms_gaval_db', 'USER': 'tms_user', 'PASSWORD': 'karma627', 'HOST': 'localhost', 'PORT': '5432'}}
DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login' # Simplificado
LOGIN_REDIRECT_URL = 'dashboard' # Simplificado
LOGOUT_REDIRECT_URL = 'login' # Simplificado
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']