import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-fallback-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Render injects the service's public hostname here; trust it automatically so
# the deploy works regardless of the generated *.onrender.com domain.
_render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

# Fail fast: never boot a public server on the insecure fallback key.
if not DEBUG and SECRET_KEY == "django-insecure-fallback-key":
    raise RuntimeError("SECRET_KEY must be set in the environment when DEBUG=False.")

# Browsers must POST cross-origin auth (e.g. the SPA at FRONTEND_URL) past CSRF.
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# ── Production security ────────────────────────────────────────────────────────
# Applied whenever DEBUG is off. Behind a TLS-terminating proxy (Render, nginx,
# load balancer), so trust the forwarded-proto header and redirect to HTTPS.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", str(60 * 60 * 24 * 365)))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "daphne",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "channels",
    # Ritha project (for signals)
    "ritha.apps.RithaConfig",
    # Ritha apps
    "auth_app",
    "wardrobe",
    "itinerary",
    "outfits",
    "cultural",
    "sustainability",
    "agents",
    "calendar_sync",
    "social",
    "messaging",
    "shared_wardrobe",
]

# ── Channels / WebSockets ──────────────────────────────────────────────────────
ASGI_APPLICATION = "ritha.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "ritha.middleware.RequestLoggingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Serve collected static files (admin, DRF browsable API, Swagger UI) directly
# from the ASGI/WSGI app via WhiteNoise. Inserted only when installed (prod),
# so dev without the package is unaffected.
try:
    import whitenoise  # noqa: F401

    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    # Legacy setting (not the STORAGES dict) so it coexists with the
    # DEFAULT_FILE_STORAGE used by the S3 media block below.
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
except ImportError:
    pass

ROOT_URLCONF = "ritha.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ritha.wsgi.application"

# ── Database ─────────────────────────────────────────────────────────────────
# Prod: set DATABASE_URL (e.g. postgres://user:pass@host:5432/dbname) — Render,
# Fly, Railway, Heroku all provide it. Dev falls back to SQLite when unset.
_database_url = os.getenv("DATABASE_URL", "")
if _database_url:
    from urllib.parse import unquote, urlparse

    _u = urlparse(_database_url)
    _engines = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
        "mysql": "django.db.backends.mysql",
        "sqlite": "django.db.backends.sqlite3",
    }
    DATABASES = {
        "default": {
            "ENGINE": _engines.get(_u.scheme, "django.db.backends.postgresql"),
            "NAME": unquote(_u.path.lstrip("/")),
            "USER": unquote(_u.username or ""),
            "PASSWORD": unquote(_u.password or ""),
            "HOST": _u.hostname or "",
            "PORT": str(_u.port or ""),
            # Reuse connections across requests; require TLS in production.
            "CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "60")),
            "OPTIONS": {"sslmode": os.getenv("DATABASE_SSLMODE", "require")}
            if _u.scheme.startswith("postgres")
            else {},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DATABASE_ENGINE", "django.db.backends.sqlite3"),
            "NAME": BASE_DIR / os.getenv("DATABASE_NAME", "db.sqlite3"),
        }
    }

# ── Custom User ────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "auth_app.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── REST Framework ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",
        "user": "500/day",
        "ai_agents": "50/day",
        "login_attempts": "20/hour",  # 20 attempts per IP per hour
        "resend_verification": "3/hour",
        "password_reset": "5/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "ritha.exceptions.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Ritha API",
    "DESCRIPTION": "AI-powered personal stylist — daily looks, trip planning, cultural intelligence.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ── JWT ────────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": os.getenv("JWT_SECRET", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    os.getenv("WEB_APP_URL", "http://localhost:3000"),
    os.getenv("MOBILE_APP_URL", "http://localhost:8081"),
]
# In production, drop any localhost/127.0.0.1 origin that slipped in via an unset
# *_APP_URL default — a localhost entry must never sit in a credentialed allowlist.
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [o for o in CORS_ALLOWED_ORIGINS if "localhost" not in o and "127.0.0.1" not in o]
# Localhost origins are only trusted in development. In production (DEBUG=False)
# these regexes are dropped so the prod API never honours a localhost Origin
# alongside CORS_ALLOW_CREDENTIALS.
CORS_ALLOWED_ORIGIN_REGEXES = (
    [
        r"^http://localhost:\d+$",
        r"^http://127\.0\.0\.1:\d+$",
    ]
    if DEBUG
    else []
)
CORS_ALLOW_CREDENTIALS = True

# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static & Media ─────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / os.getenv("MEDIA_ROOT", "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── External APIs ──────────────────────────────────────────────────────────────
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GOOGLE_CALENDAR_API_KEY = os.getenv("GOOGLE_CALENDAR_API_KEY", "")
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")

# ── Cache ─────────────────────────────────────────────────────────────────────
# Prefer Redis when REDIS_URL is set; otherwise fall back to in-process LocMem.
_redis_url = os.getenv("REDIS_URL", "")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
            "TIMEOUT": 300,
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ritha-default",
            "TIMEOUT": 300,
            "OPTIONS": {"MAX_ENTRIES": 2000},
        },
    }

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Zero-worker mode: when true, tasks run synchronously in the calling process
# instead of being shipped to a separate Celery worker. This lets a free-tier
# deploy skip the worker + beat services entirely. Trade-off: task work happens
# inline in the request (slower responses) and the beat schedule does not fire —
# fine for a demo / pre-launch, not for production throughput.
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False") == "True"
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
from celery.schedules import crontab  # noqa: E402  (imported here, next to the schedule it builds)

CELERY_BEAT_SCHEDULE = {
    "sync-all-calendars": {
        "task": "calendar.sync_all_calendars",
        "schedule": 60 * 30,
    },
    "deduplicate-events": {
        "task": "calendar.deduplicate_events",
        "schedule": 60 * 60,
    },
    "batch-daily-looks": {
        "task": "agents.batch_daily_looks",
        "schedule": crontab(hour=6, minute=0),
    },
    # §2.1 — rebuild per-user style profiles from accumulated feedback at
    # 03:00 UTC, before the daily-look batch runs at 06:00 so the new
    # profile is fresh when recommendations are generated.
    "rebuild-style-profiles": {
        "task": "agents.rebuild_style_profiles",
        "schedule": crontab(hour=3, minute=0),
    },
}

# ── Sentry (error monitoring) ─────────────────────────────────────────────────
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("APP_VERSION") or None,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    )

# ── Media storage (S3 in production) ─────────────────────────────────────────
# Activated when AWS_STORAGE_BUCKET_NAME is set in environment
_s3_bucket = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
if _s3_bucket:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_STORAGE_BUCKET_NAME = _s3_bucket
    AWS_S3_REGION_NAME = os.getenv("AWS_REGION", "eu-central-1")
    # S3-compatible endpoint override (e.g. Cloudflare R2, Backblaze B2, MinIO).
    # Leave unset for real AWS S3. For R2/B2 also set AWS_S3_CUSTOM_DOMAIN so the
    # generated MEDIA_URL points at the bucket's public/custom domain, not S3.
    _s3_endpoint = os.getenv("AWS_S3_ENDPOINT_URL", "")
    if _s3_endpoint:
        AWS_S3_ENDPOINT_URL = _s3_endpoint
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = "private"
    AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN", "")
    MEDIA_URL = (
        f"https://{AWS_S3_CUSTOM_DOMAIN}/" if AWS_S3_CUSTOM_DOMAIN else f"https://{_s3_bucket}.s3.amazonaws.com/"
    )

# ── Email ──────────────────────────────────────────────────────────────────────
# Dev: prints to console. Prod: set EMAIL_BACKEND=anymail.backends.resend.EmailBackend
# + RESEND_API_KEY (see render.yaml). SMTP vars remain as a fallback for any
# provider that prefers an SMTP relay (EMAIL_BACKEND=django...smtp.EmailBackend).
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Ritha <noreply@getritha.com>")

# Anymail / Resend (transactional email). The from-domain must be verified in
# Resend. Plain send_mail/EmailMessage work through the Anymail backend as-is.
ANYMAIL = {
    "RESEND_API_KEY": os.getenv("RESEND_API_KEY", ""),
}

# Verification token expiry (seconds)
EMAIL_VERIFICATION_TIMEOUT = int(os.getenv("EMAIL_VERIFICATION_TIMEOUT", str(60 * 60 * 24)))  # 24h

# Frontend base URL (for verification links)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ── Google Calendar OAuth ──────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# Must be registered in Google Cloud Console → OAuth 2.0 → Authorized redirect URIs
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/google/callback/")
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]

# ── Apple Calendar (CalDAV) ─────────────────────────────────────────────────────
# Credentials are provided by the user (Apple ID + App-Specific Password)
# Apple CalDAV endpoint — no OAuth, uses basic auth
APPLE_CALDAV_URL = os.getenv("APPLE_CALDAV_URL", "https://caldav.icloud.com/")

# How many days ahead to fetch events (both Google & Apple)
CALENDAR_SYNC_DAYS_AHEAD = int(os.getenv("CALENDAR_SYNC_DAYS_AHEAD", "60"))
CALENDAR_SYNC_DAYS_BEHIND = int(os.getenv("CALENDAR_SYNC_DAYS_BEHIND", "7"))

# ── Microsoft Outlook / 365 Calendar OAuth (MSAL) ─────────────────────────────
# 1. portal.azure.com → App registrations → New registration
# 2. Platform: Web — Redirect URI: http://localhost:8000/api/calendar/outlook/callback/
# 3. API permissions: Microsoft Graph → Delegated → Calendars.Read, User.Read
# 4. Certificates & secrets → New client secret
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/api/calendar/outlook/callback/")

# Outlook connection tracking (stored on User model via outlook_calendar_token)
OUTLOOK_CALENDAR_CONNECTED_FIELD = "outlook_calendar_token"

# ── Firebase Cloud Messaging (push notifications) ────────────────────────────
# Auth: gcloud auth application-default login (local dev)
#        or GOOGLE_APPLICATION_CREDENTIALS env var (prod)
