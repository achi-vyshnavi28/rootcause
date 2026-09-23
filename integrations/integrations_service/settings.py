"""Settings for the integrations service (webhooks, background processing, reconciliation)."""

import os
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "webhooks",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "integrations_service.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request",
                                       "django.contrib.auth.context_processors.auth",
                                       "django.contrib.messages.context_processors.messages"]},
}]
WSGI_APPLICATION = "integrations_service.wsgi.application"

# SQLite by default (zero setup); set INTEGRATIONS_DB=postgres to use the rootcause PostgreSQL database.
if os.getenv("INTEGRATIONS_DB") == "postgres":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("PGDATABASE", "rootcause"),
        "USER": os.getenv("PGUSER", "postgres"),
        "PASSWORD": os.getenv("PGPASSWORD", ""),
        "HOST": os.getenv("PGHOST", "127.0.0.1"),
        "PORT": os.getenv("PGPORT", "5432"),
        "OPTIONS": {"options": "-c search_path=integrations,public"},
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "integrations.sqlite3"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "static/"

REST_FRAMEWORK = {"DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination", "PAGE_SIZE": 50}

# Provider secrets (sandbox / test mode).
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
SHIPROCKET_WEBHOOK_TOKEN = os.getenv("SHIPROCKET_WEBHOOK_TOKEN", "test-shiprocket-token")
PROVIDER_API_BASE_URL = os.getenv("PROVIDER_API_BASE_URL", "http://localhost:9999")
PROVIDER_CLIENT_ID = os.getenv("PROVIDER_CLIENT_ID", "test-client")
PROVIDER_CLIENT_SECRET = os.getenv("PROVIDER_CLIENT_SECRET", "test-secret")
MAX_EVENT_ATTEMPTS = int(os.getenv("MAX_EVENT_ATTEMPTS", "5"))

# Celery: Redis in production/CI; locally (Windows, no Redis) tasks run inline ("eager").
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "memory://")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_EAGER", "1") == "1"
CELERY_TASK_ACKS_LATE = True  # a crashed worker's task is redelivered
CELERY_BEAT_SCHEDULE = {
    "nightly-reconciliation": {"task": "webhooks.tasks.run_reconciliation", "schedule": crontab(hour=2, minute=0)},
    "retry-failed-events": {"task": "webhooks.tasks.retry_failed_events", "schedule": crontab(minute="*/15")},
}

LOGGING = {
    "version": 1,
    "filters": {"mask_pii": {"()": "webhooks.pii.PiiMaskingFilter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["mask_pii"]}},
    "loggers": {"webhooks": {"handlers": ["console"], "level": "INFO"}},
}

if os.getenv("SENTRY_DSN"):
    import sentry_sdk

    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], traces_sample_rate=0.1, send_default_pii=False)
