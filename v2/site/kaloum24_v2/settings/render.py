"""Production Render + Supabase (PostgreSQL géré), en lecture/écriture.

Toutes les valeurs sensibles viennent de l'environnement ; rien n'est lu dans
un fichier ni committé. Variables :

  SECRET_KEY            obligatoire
  DATABASE_URL          obligatoire — chaîne « Session pooler » de Supabase
                        (port 5432, hôte *.pooler.supabase.com)
  SITE_URL              ex. https://kaloum24.onrender.com (sinon RENDER_EXTERNAL_URL)
  ALLOWED_HOSTS         facultatif, séparés par des virgules
  SEO_NOINDEX           « true » pour interdire l'indexation (recette)

  Médias persistants (le disque de Render est éphémère) — Supabase Storage
  via son interface S3. Sans ces variables, les images envoyées disparaissent
  à chaque redéploiement :
  AWS_STORAGE_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
  AWS_S3_ENDPOINT_URL, AWS_S3_REGION_NAME, AWS_S3_CUSTOM_DOMAIN
"""
import os
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .production import *  # noqa: F401,F403

if not os.environ.get("SECRET_KEY"):
    raise ImproperlyConfigured("SECRET_KEY est obligatoire.")
SECRET_KEY = os.environ["SECRET_KEY"]

# ---- Hôtes ----------------------------------------------------------------
SITE_URL = (os.environ.get("SITE_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "").rstrip("/")
_hotes = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
if SITE_URL:
    _hotes.append(urlsplit(SITE_URL).hostname)
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    _hotes.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
ALLOWED_HOSTS = sorted({h for h in _hotes if h and h != "*"})
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Aucun hôte autorisé : définir SITE_URL ou ALLOWED_HOSTS.")
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS]
WAGTAILADMIN_BASE_URL = SITE_URL or f"https://{ALLOWED_HOSTS[0]}"

# ---- Base de données (Supabase, Session pooler) -----------------------------
_url = os.environ.get("DATABASE_URL", "")
if not _url.startswith(("postgres://", "postgresql://")):
    raise ImproperlyConfigured("DATABASE_URL doit être une URL PostgreSQL (Supabase).")
DATABASES = {"default": dj_database_url.parse(_url, conn_max_age=0, conn_health_checks=False)}
DATABASES["default"]["OPTIONS"] = {
    "sslmode": os.environ.get("DATABASE_SSLMODE", "require"),
    "connect_timeout": 10,
    # Sûr derrière un pooler : pas de requêtes préparées côté serveur.
    "prepare_threshold": None,
}
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.postgres"]  # noqa: F405 — recherche Wagtail sur PostgreSQL

# Le cache en base du template exigerait createcachetable : on garde la mémoire
# locale (suffisant pour la limitation de débit et les caches de page courts).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ---- Sécurité ---------------------------------------------------------------
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]  # la sonde de Render parle en HTTP
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
X_FRAME_OPTIONS = "DENY"

# ---- Médias : Supabase Storage via S3 --------------------------------------
if AWS_STORAGE_BUCKET_NAME:  # noqa: F405
    # Supabase ne gère pas les ACL S3 : le bucket doit être public en lecture.
    AWS_DEFAULT_ACL = None
    AWS_S3_ADDRESSING_STYLE = "path"
    INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "wagtail_storages"]  # noqa: F405

# ---- E-mail (notifications de workflow) -------------------------------------
if os.environ.get("EMAIL_HOST"):
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "redaction@kaloum24.com")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

WAGTAIL_ENABLE_UPDATE_CHECK = False
