"""Generated-site settings: PostgreSQL/SSL, read-only until backup and approval."""
import os

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created

from .production import *  # noqa: F403
from .database import database_config, require_supabase_target, enforce_read_only_connection

if not os.environ.get("SECRET_KEY"):
    raise ImproperlyConfigured("SECRET_KEY is required.")
if not os.environ.get("ALLOWED_HOSTS") or "*" in os.environ["ALLOWED_HOSTS"]:
    raise ImproperlyConfigured("Explicit ALLOWED_HOSTS are required.")

DATABASES = {"default": database_config()}
require_supabase_target(DATABASES["default"])
if str(DATABASES["default"]["PORT"] or 5432) != "5432":
    raise ImproperlyConfigured("Read-only Django inspection requires a direct connection or Session pooler on port 5432.")
connection_created.connect(
    enforce_read_only_connection,
    dispatch_uid="kaloum24_v2_supabase_readonly",
    weak=False,
)
INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.postgres"]  # noqa: F405

# The upstream DatabaseCache writes on requests; use memory during inspection.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
