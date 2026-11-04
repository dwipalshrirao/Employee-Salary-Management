import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]


def _env(name, default=""):
    return os.getenv(name, default)


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("SECRET_KEY", "")
DEBUG = _env_bool("DEBUG", False)
if not DEBUG and not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is required when DEBUG is false.")

ALLOWED_HOSTS = [host for host in _env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host]
CSRF_TRUSTED_ORIGINS = [origin for origin in _env("CSRF_TRUSTED_ORIGINS").split(",") if origin]

SESSION_COOKIE_NAME = _env("SESSION_COOKIE_NAME", "acme_session")
SESSION_ABSOLUTE_HOURS = int(_env("SESSION_ABSOLUTE_HOURS", "8"))
SESSION_IDLE_MINUTES = int(_env("SESSION_IDLE_MINUTES", "60"))
LOGIN_MAX_FAILURES = int(_env("LOGIN_MAX_FAILURES", "5"))
LOGIN_WINDOW_MINUTES = int(_env("LOGIN_WINDOW_MINUTES", "15"))
MAX_PAGE_SIZE = int(_env("MAX_PAGE_SIZE", "100"))
BULK_MIN_PERCENT = int(_env("BULK_MIN_PERCENT", "-50"))
BULK_MAX_PERCENT = int(_env("BULK_MAX_PERCENT", "100"))
COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _env("DATABASE_PATH", str(BASE_DIR / "data" / "acme.sqlite3")),
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
            "transaction_mode": "IMMEDIATE",
            "timeout": 5,
        },
    }
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "drf_spectacular",
    "common",
    "accounts",
    "catalog",
    "employees",
    "analytics",
]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
AUTH_USER_MODEL = "accounts.HrUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.RequestMonitoringMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {},
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = COOKIE_SECURE
SESSION_COOKIE_AGE = SESSION_ABSOLUTE_HOURS * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

CSRF_USE_SESSIONS = True
CSRF_HEADER_NAME = "HTTP_X_CSRF_TOKEN"
CSRF_COOKIE_SECURE = COOKIE_SECURE

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.auth.SessionAuth"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "common.errors.handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ACME Salary Management API",
    "VERSION": "0.1.0",
    "OAS_VERSION": "3.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": "common.middleware.StructuredFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "common": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
