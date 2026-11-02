"""Offline checks only: no credentials, no migrations, no database test runner."""
import os

from django.core.exceptions import ImproperlyConfigured

if any(os.environ.get(key) for key in ("DATABASE_URL", "PGSERVICE", "PGHOST")):
    raise ImproperlyConfigured("CI checks refuse external database configuration.")

from .base import *  # noqa: E402,F403

SECRET_KEY = "ci-only-unused-for-deployment"
DEBUG = False
ALLOWED_HOSTS = ["localhost", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
