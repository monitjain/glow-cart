import os
import dj_database_url
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# ==========================================
# CORE SECURITY SETTINGS
# ==========================================

SECRET_KEY = os.environ.get('SECRET_KEY')

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY must be configured in environment variables."
    )

DEBUG = os.environ.get('DEBUG', 'True').strip().lower() in (
    'true', '1', 'yes'
)

ALLOWED_HOSTS = [
    'glowcart.co.in',
    'www.glowcart.co.in',
    'glowcart-t6bf.onrender.com',
]
if DEBUG:
    ALLOWED_HOSTS += ['localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = [
    'https://glowcart.co.in',
    'https://www.glowcart.co.in',
]

if DEBUG:
    CSRF_TRUSTED_ORIGINS += [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]


# ==========================================
# PRODUCTION SECURITY
# ==========================================

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = not DEBUG

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

SECURE_HSTS_SECONDS = 86400 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'


# ==========================================
# APPLICATIONS
# ==========================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'store',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
]


# ==========================================
# MIDDLEWARE
# ==========================================

MIDDLEWARE = [
    'mysite.middleware.RedirectOldRenderDomainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==========================================
# URLS AND TEMPLATES
# ==========================================

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'store' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'


# ==========================================
# DATABASE
# ==========================================

if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
        )
    }
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ==========================================
# PASSWORD VALIDATION
# ==========================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]


# ==========================================
# LANGUAGE AND TIME
# ==========================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ==========================================
# STATIC FILES
# ==========================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'store' / 'static'
]


# ==========================================
# MEDIA AND CLOUDINARY
# ==========================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get(
        'CLOUDINARY_CLOUD_NAME', 'dkla4wg06'
    ),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

if all([
    os.environ.get('CLOUDINARY_CLOUD_NAME'),
    os.environ.get('CLOUDINARY_API_KEY'),
    os.environ.get('CLOUDINARY_API_SECRET'),
]):
    DEFAULT_MEDIA_BACKEND = (
        'cloudinary_storage.storage.MediaCloudinaryStorage'
    )
else:
    DEFAULT_MEDIA_BACKEND = (
        'django.core.files.storage.FileSystemStorage'
    )

STORAGES = {
    'default': {
        'BACKEND': DEFAULT_MEDIA_BACKEND,
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==========================================
# AUTHENTICATION
# ==========================================

LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/'


# ==========================================
# LOGGING
# ==========================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


# ==========================================
# EMAIL CONFIGURATION
# ==========================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_TIMEOUT = 10

EMAIL_HOST_USER = os.environ.get(
    'EMAIL_HOST_USER', 'glowcart0811@gmail.com'
)

EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = (
    f'Glow Cart <{EMAIL_HOST_USER}>'
)
