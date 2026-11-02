"""Generated-site settings: PostgreSQL/SSL, read-only until backup and approval."""
import os

from django.core.exceptions import ImproperlyConfigured

from .production import *  # noqa: F403
from .database import database_config, require_supabase_target

if not os.environ.get("SECRET_KEY"):
    raise ImproperlyConfigured("SECRET_KEY is required.")
if not os.environ.get("ALLOWED_HOSTS") or "*" in os.environ["ALLOWED_HOSTS"]:
    raise ImproperlyConfigured("Explicit ALLOWED_HOSTS are required.")

DATABASES = {"default": database_config()}
require_supabase_target(DATABASES["default"])
INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.postgres"]  # noqa: F405

# The upstream DatabaseCache writes on requests; use memory during inspection.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
