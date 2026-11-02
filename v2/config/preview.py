"""Local public-interface preview. No database backend or editorial writes."""
from pathlib import Path

from .ci import *  # noqa: F403

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Conakry"
WAGTAIL_SITE_NAME = "Kaloum24"
SEO_NOINDEX = True
INSTALLED_APPS = ["django.contrib.staticfiles"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware"]
DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
ROOT_URLCONF = "kaloum24_v2.public.urls"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [Path(BASE_DIR) / "templates"],  # noqa: F405
    "APP_DIRS": False,
    "OPTIONS": {
        "loaders": ["django.template.loaders.filesystem.Loader"],
        "context_processors": ["django.template.context_processors.request"],
    },
}]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
