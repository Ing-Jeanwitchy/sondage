"""
Django settings for core project.
Plateforme de Sondage Électoral – Nord-Ouest, Haïti
Architecture : Frontend (Firebase Hosting), Backend (Render), Médias (Cloudinary)
"""

from pathlib import Path
import os
import sys
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Charger les variables d'environnement (.env si présent)
load_dotenv(BASE_DIR / '.env')

# Ajouter le dossier 'apps' au path Python pour imports propres
APPS_DIR = BASE_DIR / 'apps'
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# Clé secrète et debug
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

_secret_key = os.getenv('SECRET_KEY', '').strip()
if not _secret_key:
    if DEBUG:
        import warnings
        _secret_key = 'django-dev-only-insecure-key-DO-NOT-USE-IN-PRODUCTION'
        warnings.warn(
            "⚠️  SECRET_KEY manquante ! Utilisation d'une clé de développement temporaire. "
            "Définissez SECRET_KEY dans votre fichier .env avant tout déploiement en production.",
            UserWarning,
            stacklevel=1,
        )
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "ERREUR CRITIQUE : La variable d'environnement SECRET_KEY est obligatoire en production. "
            "Ajoutez SECRET_KEY dans vos variables d'environnement (Render, .env, etc.)."
        )
SECRET_KEY = _secret_key

# Domaines autorisés
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',') if h.strip()]
if '.onrender.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.onrender.com')

# Définition des applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Dépendances tierces
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',

    # Stockage Cloudinary (Actif si les clés sont fournies)
    'cloudinary_storage',
    'cloudinary',

    # Applications locales
    'accounts',
    'elections',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Doit être avant CommonMiddleware
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Fichiers statiques sur Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Configuration Base de données
# Par défaut SQLite en local, ou Neon Serverless PostgreSQL via DATABASE_URL
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Si connexion Neon avec pooler (PgBouncer), conn_max_age doit être 0
    is_pooled = 'pooler' in database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=0 if is_pooled else int(os.getenv('CONN_MAX_AGE', 600)),
            conn_health_checks=True,
        )
    }
    # Neon requiert SSL obligatoire
    if 'neon.tech' in database_url or 'sslmode' in database_url:
        DATABASES['default'].setdefault('OPTIONS', {})
        DATABASES['default']['OPTIONS']['sslmode'] = 'require'
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Validation des mots de passe
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Paramètres régionaux et fuseau horaire d'Haïti
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'America/Port-au-Prince'
USE_I18N = True
USE_TZ = True

# Fichiers statiques
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Médias locaux (fallback si Cloudinary n'est pas configuré)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Configuration Cloudinary (Médias dans le cloud)
CLOUDINARY_URL = os.getenv('CLOUDINARY_URL', '').strip()
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '').strip()
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '').strip()
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '').strip()

# Si CLOUDINARY_URL founi (fòma: cloudinary://API_KEY:API_SECRET@CLOUD_NAME)
if CLOUDINARY_URL and not CLOUDINARY_CLOUD_NAME:
    import re
    match = re.match(r'cloudinary://([^:]+):([^@]+)@(.+)', CLOUDINARY_URL)
    if match:
        CLOUDINARY_API_KEY = match.group(1)
        CLOUDINARY_API_SECRET = match.group(2)
        CLOUDINARY_CLOUD_NAME = match.group(3)

IS_CLOUDINARY_ACTIVE = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET) or bool(CLOUDINARY_URL)

if IS_CLOUDINARY_ACTIVE:
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuration Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/minute',
        'user': '300/minute',
        'auth': '30/minute',
        'votes': '15/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Durcissement de la sécurité HTTP
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# Configuration SimpleJWT durcie (2 heures au lieu de 7 jours)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Configuration CORS dynamique (Firebase Hosting nordoeust + Dev Local)
CORS_ALLOW_CREDENTIALS = True

# Domèn Firebase ofisyèl pwojè nordoeust
FIREBASE_DOMAINS = [
    'https://nordoeust.web.app',
    'https://nordoeust.firebaseapp.com',
]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = FIREBASE_DOMAINS
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://.*\.web\.app$",
        r"^https://.*\.firebaseapp.com$",
        r"^http://localhost:[0-9]+$",
        r"^http://127\.0\.0\.1:[0-9]+$",
    ]
    extra_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
    if extra_origins:
        CORS_ALLOWED_ORIGINS += [o.strip() for o in extra_origins.split(',') if o.strip()]

# Limit telechajman fichye (25 MB pou pèmèt foto jiska 20 Mo)
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25 MB
