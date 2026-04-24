"""
Production settings for Ritha.
Inherits from settings.py and overrides for production deployment.

Usage:
  DJANGO_SETTINGS_MODULE=ritha.settings_production python manage.py ...
"""
from .settings import *  # noqa: F401, F403
import os

# ── Security ──────────────────────────────────────────────────────────────────
DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']          # Must be set — never use default in prod
ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')

SECURE_PROXY_SSL_HEADER      = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT          = os.environ.get('SECURE_SSL_REDIRECT', 'true').lower() == 'true'
SECURE_HSTS_SECONDS          = 31_536_000      # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD          = True
SESSION_COOKIE_SECURE        = True
CSRF_COOKIE_SECURE           = True
SECURE_BROWSER_XSS_FILTER    = True
SECURE_CONTENT_TYPE_NOSNIFF  = True
X_FRAME_OPTIONS              = 'DENY'

# ── Database (PostgreSQL) ─────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ['DB_NAME'],
        'USER':     os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST':     os.environ.get('DB_HOST', 'db'),
        'PORT':     os.environ.get('DB_PORT', '5432'),
        'OPTIONS':  {
            'sslmode': os.environ.get('DB_SSLMODE', 'require'),
        },
        'CONN_MAX_AGE': 60,
    }
}

# ── Cache (Redis) ─────────────────────────────────────────────────────────────
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS':  {'socket_timeout': 5},
    }
}

# Throttle storage uses cache backend — works automatically once Redis is set
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {
        'anon':      '20/hour',
        'user':      '500/day',
        'ai_agents': '50/day',
    },
}

# ── Media / Static ────────────────────────────────────────────────────────────
# In production, serve media via S3-compatible storage
# Uncomment and configure when ready:
# DEFAULT_FILE_STORAGE    = 'storages.backends.s3boto3.S3Boto3Storage'
# STATICFILES_STORAGE     = 'storages.backends.s3boto3.StaticS3Boto3Storage'
# AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
# AWS_S3_REGION_NAME      = os.environ.get('AWS_REGION', 'eu-central-1')
STATIC_ROOT = BASE_DIR / 'staticfiles'  # noqa: F405

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version':            1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level':    'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level':    os.environ.get('DJANGO_LOG_LEVEL', 'ERROR'),
            'propagate': False,
        },
        'ritha': {
            'handlers': ['console'],
            'level':    'INFO',
            'propagate': False,
        },
    },
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'https://ritha.com,https://app.ritha.com'
).split(',')
