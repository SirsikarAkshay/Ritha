import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_celery_beat',
    'channels',
    # Arokah project (for signals)
    'arokah.apps.ArokahConfig',
    # Arokah apps
    'auth_app',
    'wardrobe',
    'itinerary',
    'outfits',
    'cultural',
    'sustainability',
    'agents',
    'calendar_sync',
    'social',
    'messaging',
    'shared_wardrobe',
]

# ── Channels / WebSockets ──────────────────────────────────────────────────────
ASGI_APPLICATION = 'arokah.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.getenv('REDIS_URL', 'redis://localhost:6379/0')],
        },
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'arokah.middleware.RequestLoggingMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'arokah.urls'

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

WSGI_APPLICATION = 'arokah.wsgi.application'

# ── Database (SQLite) ──────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': BASE_DIR / os.getenv('DATABASE_NAME', 'db.sqlite3'),
    }
}

# ── Custom User ────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'auth_app.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── REST Framework ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon':               '20/hour',
        'user':               '500/day',
        'ai_agents':          '50/day',
        'login_attempts':     '20/hour',   # 20 attempts per IP per hour
        'resend_verification': '3/hour',
        'password_reset':      '5/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'arokah.exceptions.custom_exception_handler',
}

SPECTACULAR_SETTINGS = {
    'TITLE':       'Arokah API',
    'DESCRIPTION': 'AI-powered personal stylist — daily looks, trip planning, cultural intelligence.',
    'VERSION':     '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# ── JWT ────────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'SIGNING_KEY': os.getenv('JWT_SECRET', SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    os.getenv('WEB_APP_URL', 'http://localhost:3000'),
    os.getenv('MOBILE_APP_URL', 'http://localhost:8081'),
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^http://localhost:\d+$',
    r'^http://127\.0\.0\.1:\d+$',
]
CORS_ALLOW_CREDENTIALS = True

# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── Static & Media ─────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
MEDIA_ROOT = BASE_DIR / os.getenv('MEDIA_ROOT', 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── External APIs ──────────────────────────────────────────────────────────────
MISTRAL_API_KEY         = os.getenv('MISTRAL_API_KEY', '')
GOOGLE_CALENDAR_API_KEY = os.getenv('GOOGLE_CALENDAR_API_KEY', '')
GOOGLE_VISION_API_KEY   = os.getenv('GOOGLE_VISION_API_KEY', '')

# ── Cache ─────────────────────────────────────────────────────────────────────
# Prefer Redis when REDIS_URL is set; otherwise fall back to in-process LocMem.
_redis_url = os.getenv('REDIS_URL', '')
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_url,
            'TIMEOUT': 300,
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'arokah-default',
            'TIMEOUT': 300,
            'OPTIONS': {'MAX_ENTRIES': 2000},
        },
    }

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL            = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND        = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT        = ['json']
CELERY_TASK_SERIALIZER       = 'json'
CELERY_RESULT_SERIALIZER     = 'json'
CELERY_TIMEZONE              = TIME_ZONE
CELERY_BEAT_SCHEDULER        = 'django_celery_beat.schedulers:DatabaseScheduler'

# ── Sentry (error monitoring) ─────────────────────────────────────────────────
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# ── Media storage (S3 in production) ─────────────────────────────────────────
# Activated when AWS_STORAGE_BUCKET_NAME is set in environment
_s3_bucket = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
if _s3_bucket:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_STORAGE_BUCKET_NAME = _s3_bucket
    AWS_S3_REGION_NAME      = os.getenv('AWS_REGION', 'eu-central-1')
    AWS_S3_FILE_OVERWRITE   = False
    AWS_DEFAULT_ACL         = 'private'
    AWS_S3_CUSTOM_DOMAIN    = os.getenv('AWS_S3_CUSTOM_DOMAIN', '')
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/' if AWS_S3_CUSTOM_DOMAIN else f'https://{_s3_bucket}.s3.amazonaws.com/'

# ── Email ──────────────────────────────────────────────────────────────────────
# Development: print emails to console (no SMTP needed)
EMAIL_BACKEND     = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST        = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT        = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS     = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER   = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = os.getenv('DEFAULT_FROM_EMAIL', 'Arokah <noreply@arokah.com>')

# Verification token expiry (seconds)
EMAIL_VERIFICATION_TIMEOUT = int(os.getenv('EMAIL_VERIFICATION_TIMEOUT', str(60 * 60 * 24)))  # 24h

# Frontend base URL (for verification links)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# ── Google Calendar OAuth ──────────────────────────────────────────────────────
GOOGLE_CLIENT_ID      = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET  = os.getenv('GOOGLE_CLIENT_SECRET', '')
# Must be registered in Google Cloud Console → OAuth 2.0 → Authorized redirect URIs
GOOGLE_REDIRECT_URI   = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/calendar/google/callback/')
GOOGLE_CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
]

# ── Apple Calendar (CalDAV) ─────────────────────────────────────────────────────
# Credentials are provided by the user (Apple ID + App-Specific Password)
# Apple CalDAV endpoint — no OAuth, uses basic auth
APPLE_CALDAV_URL = os.getenv('APPLE_CALDAV_URL', 'https://caldav.icloud.com/')

# How many days ahead to fetch events (both Google & Apple)
CALENDAR_SYNC_DAYS_AHEAD = int(os.getenv('CALENDAR_SYNC_DAYS_AHEAD', '60'))
CALENDAR_SYNC_DAYS_BEHIND = int(os.getenv('CALENDAR_SYNC_DAYS_BEHIND', '7'))

# ── Microsoft Outlook / 365 Calendar OAuth (MSAL) ─────────────────────────────
# 1. portal.azure.com → App registrations → New registration
# 2. Platform: Web — Redirect URI: http://localhost:8000/api/calendar/outlook/callback/
# 3. API permissions: Microsoft Graph → Delegated → Calendars.Read, User.Read
# 4. Certificates & secrets → New client secret
MICROSOFT_CLIENT_ID      = os.getenv('MICROSOFT_CLIENT_ID', '')
MICROSOFT_CLIENT_SECRET  = os.getenv('MICROSOFT_CLIENT_SECRET', '')
MICROSOFT_REDIRECT_URI   = os.getenv('MICROSOFT_REDIRECT_URI',
                                      'http://localhost:8000/api/calendar/outlook/callback/')

# Outlook connection tracking (stored on User model via outlook_calendar_token)
OUTLOOK_CALENDAR_CONNECTED_FIELD = 'outlook_calendar_token'
