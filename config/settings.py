"""
Django settings for LogiRate API (Courier Module).

Production-ready settings with environment-based configuration.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

# Environment: 'development', 'staging', 'production'
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-s7fy1h1&v8qy__#8#s5&@-&jnfd)+rnz&4^jym+5by_cayrj6p')

# Validate secret key in production
if ENVIRONMENT == 'production' and SECRET_KEY.startswith('django-insecure'):
    raise RuntimeError("CRITICAL: Using insecure SECRET_KEY in production!")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Validate DEBUG is off in production
if ENVIRONMENT == 'production' and DEBUG:
    raise RuntimeError("CRITICAL: DEBUG must be False in production!")

# ALLOWED_HOSTS - strict in production
if ENVIRONMENT == 'production':
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
    ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise RuntimeError("CRITICAL: ALLOWED_HOSTS must be explicitly set in production (no wildcards)!")
else:
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# Admin Password Validation
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError(
        "CRITICAL: ADMIN_PASSWORD not set in .env file. "
        "Set a strong password (12+ characters, mix of letters/numbers/symbols)."
    )
elif len(ADMIN_PASSWORD) < 12:
    raise RuntimeError("CRITICAL: ADMIN_PASSWORD is too weak. Password must be at least 12 characters long.")
elif ADMIN_PASSWORD in ["Transportwale", "admin", "password", "12345678", "admin123"]:
    raise RuntimeError("CRITICAL: ADMIN_PASSWORD is a common/default password.")
elif ADMIN_PASSWORD.isalpha() or ADMIN_PASSWORD.isdigit():
    raise RuntimeError("CRITICAL: ADMIN_PASSWORD is too simple. Must contain letters, numbers, and symbols.")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "courier",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS - must be before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "static"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Use PostgreSQL if DB_NAME is set, otherwise fall back to SQLite
if os.getenv('DB_NAME'):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv('DB_NAME', 'courier_db'),
            "USER": os.getenv('DB_USER', 'courier_user'),
            "PASSWORD": os.getenv('DB_PASSWORD', 'courier_pass'),
            "HOST": os.getenv('DB_HOST', 'localhost'),
            "PORT": os.getenv('DB_PORT', '5432'),
        }
    }
else:
    # Fallback to SQLite for backward compatibility
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "logistics.db",
        }
    }
    
    # Block SQLite in production - PostgreSQL is required for reliability and performance
    if ENVIRONMENT == 'production':
        raise RuntimeError(
            "CRITICAL: SQLite is not allowed in production! "
            "Configure PostgreSQL by setting DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, and DB_PORT environment variables."
        )


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# CORS Configuration
# =============================================================================

if ENVIRONMENT == 'production':
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
    CORS_ALLOWED_ORIGINS = [o.strip() for o in CORS_ALLOWED_ORIGINS if o.strip()]
    if not CORS_ALLOWED_ORIGINS:
        # Default to ALLOWED_HOSTS with https
        CORS_ALLOWED_ORIGINS = [f'https://{h}' for h in ALLOWED_HOSTS]
else:
    # Allow all origins in development
    CORS_ALLOW_ALL_ORIGINS = True

# CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-admin-token',  # Custom admin header
]

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'courier.authentication.AdminTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',  # Match FastAPI rate limit
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# DRF Spectacular Settings (API Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'LogiRate API',
    'DESCRIPTION': 'Shipping cost comparison engine for Indian logistics',
    'VERSION': '1.0.0',
    'CONTACT': {'email': 'support@example.com'},
    'LICENSE': {'name': 'MIT'},
}

# Logging Configuration (matching FastAPI setup)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'app.log',
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 2,
            'formatter': 'standard',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'courier': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# PRODUCTION SECURITY SETTINGS
# =============================================================================

if ENVIRONMENT == 'production' or not DEBUG:
    # HTTPS/SSL
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HTTP Strict Transport Security
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookie security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    
    # XSS and content security
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Disable browsable API in production
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
        'rest_framework.renderers.JSONRenderer',
    ]

# =============================================================================
# PASSWORD HASHERS (Argon2 prioritized)
# =============================================================================

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# =============================================================================
# CACHING (Redis in production, local memory in dev)
# =============================================================================

REDIS_URL = os.getenv('REDIS_URL')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'courier',
            'TIMEOUT': 300,  # 5 minutes default
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# =============================================================================
# SENTRY ERROR MONITORING (Production)
# =============================================================================

SENTRY_DSN = os.getenv('SENTRY_DSN')

if SENTRY_DSN and ENVIRONMENT == 'production':
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                LoggingIntegration(
                    level=None,  # Capture all log levels
                    event_level=None,  # Send all as breadcrumbs
                ),
            ],
            traces_sample_rate=0.1,  # 10% of transactions
            send_default_pii=False,  # Don't send PII
            environment=ENVIRONMENT,
        )
    except ImportError:
        pass  # sentry-sdk not installed


# =============================================================================
# DATA UPLOAD SETTINGS
# =============================================================================

# Increase field limit for Admin panel (to support large city lists)
DATA_UPLOAD_MAX_NUMBER_FIELDS = None
