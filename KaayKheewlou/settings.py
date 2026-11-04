"""
Django settings for KaayKheewlou project.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-as_xpi8su@t_wthgs1)w!52)=y4m4ec7x4wp!u$)z1%vo9@pci'

DEBUG = True

ALLOWED_HOSTS = ['*']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'monapp',
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

ROOT_URLCONF = 'KaayKheewlou.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'monapp.context_processors.panier_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'KaayKheewlou.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'Africa/Dakar'

USE_I18N = True

USE_TZ = True


# Static & media files (100% locaux, aucune dépendance internet / CDN externe)
STATIC_URL = 'static/'
STATICFILES_DIRS = []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentification "gestion" (espace administrateur Kaay Kheewlou)
LOGIN_URL = '/gestion/connexion/'
LOGIN_REDIRECT_URL = '/gestion/'
LOGOUT_REDIRECT_URL = '/gestion/connexion/'

# Frais de livraison fixes (FCFA) — aucune API externe requise
FRAIS_LIVRAISON = 1500

# Identifiants de démonstration créés par la commande "seed_data"
ADMIN_USERNAME = 'admin123'
ADMIN_PASSWORD = 'admin123'

# Programme de fidélité : 1 point gagné par tranche de FCFA dépensée
# (commande "terminée"), et valeur de reprise d'un point en réduction.
POINTS_SEUIL_FCFA = 1000
POINT_VALEUR_REDUCTION = 25
