"""
Configuration Django du projet SILIMU
Conception et réalisation d'une application web de gestion de réservation
de billets de transport lacustre — cas de l'établissement SILIMU.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# --------------------------------------------------------------------
# Sécurité
# --------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'dev-only-secret-key-change-me-before-production'
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# --------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'rest_framework',

    'reservations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'silimu.urls'

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
                'reservations.context_processors.role_utilisateur',
            ],
        },
    },
]

WSGI_APPLICATION = 'silimu.wsgi.application'
ASGI_APPLICATION = 'silimu.asgi.application'

# --------------------------------------------------------------------
# Base de données — Supabase PostgreSQL / PostgreSQL autonome / SQLite
# --------------------------------------------------------------------
# Si SUPABASE_URL est défini, on utilise la chaîne de connexion Supabase.
# Sinon, on utilise les variables DB_* classiques, ou SQLite par défaut.
SUPABASE_DATABASE_URL = os.environ.get('SUPABASE_DATABASE_URL', '')
if SUPABASE_DATABASE_URL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'postgres'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'db.<votre-projet>.supabase.co'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
elif os.environ.get('DB_ENGINE', '').lower() in ('postgresql', 'postgres', 'psql') or os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'silimu_db'),
            'USER': os.environ.get('DB_USER', 'silimu_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'silimu_pass'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --------------------------------------------------------------------
# Validation des mots de passe
# --------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Kinshasa'
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------
# Fichiers statiques
# --------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------------------------------------------------
# Authentification — espace admin SILIMU
# --------------------------------------------------------------------
LOGIN_URL = 'admin_login'
LOGIN_REDIRECT_URL = 'admin_dashboard'
LOGOUT_REDIRECT_URL = 'home'

# --------------------------------------------------------------------
# Paiement Mobile Money — CinetPay
# --------------------------------------------------------------------
# À récupérer dans le tableau de bord CinetPay > Intégrations, après
# création d'un compte marchand sur https://www.cinetpay.com
CINETPAY_API_KEY = os.environ.get('CINETPAY_API_KEY', '')
CINETPAY_SITE_ID = os.environ.get('CINETPAY_SITE_ID', '')
CINETPAY_CURRENCY = os.environ.get('CINETPAY_CURRENCY', 'CDF')  # XOF, XAF, CDF, GNF

# --------------------------------------------------------------------
# E-mail — envoi du billet + alerte de remplissage
# --------------------------------------------------------------------
# Par défaut : les e-mails s'affichent dans le terminal (aucun compte requis).
# Si BREVO_API_KEY est défini, les e-mails sont envoyés via l'API Brevo.
# Pour un SMTP classique, définir DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# et les variables EMAIL_HOST / EMAIL_PORT / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / EMAIL_USE_TLS.
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'reservations.brevo_email_backend.BrevoEmailBackend' if BREVO_API_KEY
    else 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'SILIMU <no-reply@silimu.local>')
BREVO_SENDER_EMAIL = os.environ.get('BREVO_SENDER_EMAIL', 'no-reply@silimu.local')

# --------------------------------------------------------------------
# Supabase — Base de données PostgreSQL, Auth & Storage
# --------------------------------------------------------------------
# 1. Crée un projet sur https://supabase.com
# 2. Récupère les identifiants dans Settings > API
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
# Nom du bucket Storage pour les billets / QR codes
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'billets')
# Durée de validité du lien signé (secondes)
SUPABASE_STORAGE_EXPIRY = int(os.environ.get('SUPABASE_STORAGE_EXPIRY', '3600'))
# Collection Supabase Auth mappée au modèle Passager (via auth.users)
SUPABASE_AUTH_TABLE = os.environ.get('SUPABASE_AUTH_TABLE', 'passagers')

# Adresse recevant les alertes de remplissage et autres notifications internes
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')
# Taux de remplissage (%) déclenchant l'alerte automatique
SEUIL_ALERTE_REMPLISSAGE = int(os.environ.get('SEUIL_ALERTE_REMPLISSAGE', '90'))
# Nombre d'heures avant le départ à partir duquel le rappel automatique est envoyé
RAPPEL_HEURES_AVANT = int(os.environ.get('RAPPEL_HEURES_AVANT', '24'))

# --------------------------------------------------------------------
# API REST (Django REST Framework)
# --------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'reservations.auth_backends.SupabaseAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
