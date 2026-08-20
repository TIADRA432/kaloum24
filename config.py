import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _bool(name, default="0"):
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


class Config:
    # ---------- Identité du site ----------
    SITE_NAME = os.environ.get("SITE_NAME", "Kaloum24")
    SITE_TAGLINE = os.environ.get("SITE_TAGLINE", "L'actualité en continu")
    SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:5000")
    SITE_DESCRIPTION = os.environ.get(
        "SITE_DESCRIPTION",
        "Toute l'actualité en continu : politique, économie, société, sport et culture.",
    )
    SITE_LOCALE = os.environ.get("SITE_LOCALE", "fr_FR")

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-moi-en-production-svp")

    # ---------- Base de données ----------
    # Render (comme Heroku en son temps) fournit une URL postgres:// —
    # SQLAlchemy 1.4+ exige postgresql:// et refuse l'ancien préfixe.
    # Sans cette normalisation, la connexion échoue net au démarrage sur
    # tout hébergeur qui suit encore cette convention historique.
    _db_url = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'kaloum24.db')}"
    )
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    ARTICLES_PER_PAGE = 10

    # ---------- Upload d'images ----------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024          # 8 Mo par requête
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    IMAGE_MAX_WIDTH = 1600                        # redimensionnement automatique
    IMAGE_QUALITY = 82

    # ---------- Réseaux sociaux (laisser vide pour masquer le lien) ----------
    SOCIAL_X = os.environ.get("SOCIAL_X", "")
    SOCIAL_WHATSAPP_CHANNEL = os.environ.get("SOCIAL_WHATSAPP_CHANNEL", "")
    SOCIAL_FACEBOOK = os.environ.get("SOCIAL_FACEBOOK", "")
    SOCIAL_YOUTUBE = os.environ.get("SOCIAL_YOUTUBE", "")
    SOCIAL_INSTAGRAM = os.environ.get("SOCIAL_INSTAGRAM", "")
    SOCIAL_TIKTOK = os.environ.get("SOCIAL_TIKTOK", "")

    # ---------- Météo (Open-Meteo : gratuit, sans clé API) ----------
    WEATHER_ENABLED = _bool("WEATHER_ENABLED", "1")
    WEATHER_CITY = os.environ.get("WEATHER_CITY", "Conakry")
    WEATHER_LAT = float(os.environ.get("WEATHER_LAT", "9.6412"))
    WEATHER_LON = float(os.environ.get("WEATHER_LON", "-13.5784"))
    WEATHER_TIMEZONE = os.environ.get("WEATHER_TIMEZONE", "Africa/Conakry")

    # ---------- Lecture audio (synthèse vocale du navigateur) ----------
    TTS_ENABLED = _bool("TTS_ENABLED", "1")
    TTS_LANG = os.environ.get("TTS_LANG", "fr-FR")

    # ---------- Publication par WhatsApp (correspondants) ----------
    # Utilise l'API Cloud de Meta, gratuite jusqu'à un volume de conversations
    # largement suffisant pour un flux de rédaction interne.
    WHATSAPP_ENABLED = _bool("WHATSAPP_ENABLED", "0")
    WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")
    # Jeton arbitraire choisi par l'administrateur, à saisir aussi côté Meta
    # lors de la configuration du webhook (poignée de main de vérification).
    WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    # Jeton d'accès de l'application Meta — permet d'envoyer des messages et
    # de télécharger les médias reçus.
    WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    # Secret de l'app Meta, sert à vérifier que les webhooks reçus viennent
    # bien de Meta (signature HMAC) et non d'un tiers.
    WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")
    # Indicatif pays (sans +) utilisé pour compléter les numéros saisis au
    # format local par l'administrateur. 224 = Guinée. À adapter si ce site
    # est déployé pour un client dans un autre pays.
    WHATSAPP_COUNTRY_CODE = os.environ.get("WHATSAPP_COUNTRY_CODE", "224")
    # Rubrique assignée par défaut aux articles créés par WhatsApp (le slug,
    # pas le nom affiché) — un correspondant ne choisit pas de rubrique par
    # message, la rédaction la corrige si besoin avant publication.
    WHATSAPP_DEFAULT_CATEGORY = os.environ.get("WHATSAPP_DEFAULT_CATEGORY", "societe")

    # ---------- E-mail (réinitialisation de mot de passe) ----------
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", "1")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_SENDER = os.environ.get("MAIL_SENDER", "no-reply@example.com")
    RESET_TOKEN_MAX_AGE = 3600                    # 1 heure

    # ---------- Limitation de débit ----------
    # Protège la connexion, l'inscription, les commentaires et la
    # réinitialisation de mot de passe contre le bourrage et le spam.
    RATELIMIT_ENABLED = _bool("RATELIMIT_ENABLED", "1")
    # En mémoire par défaut : suffisant pour un seul processus. Avec plusieurs
    # workers gunicorn, chaque worker aurait son propre compteur — utilise
    # alors Redis (ex. redis://localhost:6379) pour un décompte partagé.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_LOGIN = os.environ.get("RATELIMIT_LOGIN", "10 per 5 minutes")
    RATELIMIT_REGISTER = os.environ.get("RATELIMIT_REGISTER", "5 per hour")
    RATELIMIT_COMMENT = os.environ.get("RATELIMIT_COMMENT", "10 per 10 minutes")
    RATELIMIT_PASSWORD_RESET = os.environ.get("RATELIMIT_PASSWORD_RESET", "5 per hour")
    RATELIMIT_WEBHOOK = os.environ.get("RATELIMIT_WEBHOOK", "120 per minute")

    # ---------- Sécurité / production ----------
    # ENV=production active les protections strictes : cookies en HTTPS
    # uniquement, HSTS, et refus de démarrer avec une clé secrète par défaut.
    ENV = os.environ.get("ENV", "development")
    IS_PRODUCTION = ENV.lower() in ("production", "prod")

    # ---------- Modération des commentaires ----------
    # Par défaut, TOUT commentaire attend une validation humaine avant
    # d'être visible (pré-modération) — le comportement le plus sûr, en
    # place depuis le début de ce projet. Activer COMMENT_AUTO_APPROVE
    # bascule vers une post-modération : un commentaire qui passe les
    # filtres automatiques ci-dessous s'affiche immédiatement ; un
    # commentaire suspect part quand même en file d'attente, quel que soit
    # ce réglage — le filtre ne rejette jamais silencieusement, il ralentit
    # seulement ce qui a l'air suspect.
    COMMENT_AUTO_APPROVE = _bool("COMMENT_AUTO_APPROVE", "0")
    COMMENT_MAX_LIENS = int(os.environ.get("COMMENT_MAX_LIENS", "1"))
    COMMENT_SPAM_KEYWORDS = os.environ.get(
        "COMMENT_SPAM_KEYWORDS",
        "viagra, casino, crypto gratuit, gagner de l'argent, cliquez ici, "
        "xxx, rencontre adulte, pret immediat, forex",
    )

    # Cookies de session : jamais lisibles en JavaScript, non transmis lors
    # d'une navigation depuis un site tiers, et réservés à HTTPS en production.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_SAMESITE = "Lax"

    SECURITY_HEADERS_ENABLED = _bool("SECURITY_HEADERS_ENABLED", "1")
    # HSTS : indique aux navigateurs de n'utiliser que HTTPS. À n'activer
    # qu'une fois le certificat en place — sinon le site devient inaccessible
    # pour les visiteurs déjà venus, et ce pour la durée annoncée.
    HSTS_ENABLED = _bool("HSTS_ENABLED", "0")
    HSTS_MAX_AGE = int(os.environ.get("HSTS_MAX_AGE", "31536000"))

    # Nombre de proxys de confiance devant l'application (Nginx = 1). Sert à
    # lire la vraie IP du visiteur dans X-Forwarded-For : sans cela, la
    # limitation de débit verrait tout le trafic venir du proxy et
    # bloquerait tout le monde d'un coup.
    PROXY_COUNT = int(os.environ.get("PROXY_COUNT", "0"))

    # ---------- Journalisation ----------
    LOG_TO_FILE = _bool("LOG_TO_FILE", "0")
    LOG_DIR = os.environ.get("LOG_DIR", os.path.join(BASE_DIR, "logs"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))

    # ---------- Stripe ----------
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    SUBSCRIPTION_PRICE_LABEL = os.environ.get("SUBSCRIPTION_PRICE_LABEL", "15 000 GNF / mois")
