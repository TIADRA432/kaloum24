"""Durcissement pour la mise en production.

Regroupe trois choses distinctes mais toutes liées au passage en production :
en-têtes de sécurité HTTP, validation de la configuration au démarrage, et
journalisation dans des fichiers avec rotation.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

CLES_PAR_DEFAUT = {
    "change-moi-en-production-svp",
    "remplace-moi-par-une-longue-chaine-aleatoire",
    "cle-de-test",
    "secret",
    "dev",
}


# --------------------------------------------------------- en-têtes HTTP

def enregistrer_entetes_securite(app):
    """Ajoute les en-têtes de sécurité à chaque réponse.

    La politique de sécurité du contenu (CSP) est volontairement permissive
    sur les styles et scripts en ligne : les gabarits en contiennent
    (bascule de thème, données structurées). Elle bloque néanmoins le
    chargement de scripts depuis un domaine tiers, ce qui reste la protection
    la plus utile contre une injection réussie.
    """
    if not app.config["SECURITY_HEADERS_ENABLED"]:
        return

    csp = "; ".join([
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ])

    @app.after_request
    def _entetes(response):
        response.headers.setdefault("Content-Security-Policy", csp)
        # Empêche l'affichage du site dans une iframe (clickjacking).
        response.headers.setdefault("X-Frame-Options", "DENY")
        # Empêche le navigateur de deviner un type de contenu différent de
        # celui annoncé — évite qu'un fichier envoyé soit interprété en HTML.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )

        if app.config["HSTS_ENABLED"]:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={app.config['HSTS_MAX_AGE']}; includeSubDomains",
            )
        return response


# ------------------------------------------------ validation au démarrage

def verifier_configuration(app, strict=None):
    """Contrôle la configuration et retourne (erreurs, avertissements).

    En production, une erreur empêche le démarrage : mieux vaut un service
    qui refuse de partir avec un message clair qu'un site en ligne avec une
    clé secrète connue de tous.
    """
    if strict is None:
        strict = app.config["IS_PRODUCTION"]

    erreurs, avertissements = [], []

    if app.config["SECRET_KEY"] in CLES_PAR_DEFAUT or len(app.config["SECRET_KEY"]) < 32:
        message = (
            "SECRET_KEY est celle par défaut ou trop courte. Génère-la avec : "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
        (erreurs if strict else avertissements).append(message)

    if app.config["DEBUG"] and strict:
        erreurs.append("Le mode debug est actif en production : expose le code et permet l'exécution de commandes.")

    url = app.config["SITE_URL"]
    if strict:
        if "127.0.0.1" in url or "localhost" in url:
            erreurs.append(
                f"SITE_URL vaut « {url} » : les partages WhatsApp, le flux RSS "
                "et le sitemap pointeront vers une adresse locale."
            )
        elif not url.startswith("https://"):
            avertissements.append(f"SITE_URL n'utilise pas HTTPS ({url}).")

    if strict and not app.config["HSTS_ENABLED"]:
        avertissements.append(
            "HSTS désactivé. Active HSTS_ENABLED=1 une fois le certificat HTTPS en place."
        )

    if strict and app.config["PROXY_COUNT"] == 0:
        avertissements.append(
            "PROXY_COUNT=0 : derrière Nginx, mets PROXY_COUNT=1, sinon la "
            "limitation de débit voit toutes les requêtes venir du proxy et "
            "bloquera tous les visiteurs ensemble."
        )

    if strict and app.config["RATELIMIT_STORAGE_URI"].startswith("memory://"):
        avertissements.append(
            "Compteurs de débit en mémoire : avec plusieurs workers, la limite "
            "réelle est multipliée par leur nombre. Utilise Redis pour un décompte exact."
        )

    if app.config["WHATSAPP_ENABLED"] and not app.config["WHATSAPP_APP_SECRET"]:
        message = ("WHATSAPP_ENABLED=1 sans WHATSAPP_APP_SECRET : le webhook accepte "
                   "des requêtes sans vérifier qu'elles viennent de Meta.")
        (erreurs if strict else avertissements).append(message)

    if app.config["IS_PRODUCTION"] and not app.config["SESSION_COOKIE_SECURE"]:
        erreurs.append("Les cookies de session ne sont pas restreints à HTTPS.")

    return erreurs, avertissements


def appliquer_verification_demarrage(app):
    """Journalise le diagnostic et interrompt le démarrage si nécessaire."""
    erreurs, avertissements = verifier_configuration(app)

    for a in avertissements:
        app.logger.warning("Configuration : %s", a)

    if erreurs:
        for e in erreurs:
            app.logger.error("Configuration : %s", e)
        # En production uniquement : refuser de démarrer plutôt que de servir
        # un site vulnérable en silence.
        if app.config["IS_PRODUCTION"]:
            print("\n=== Démarrage interrompu : configuration de production invalide ===",
                  file=sys.stderr)
            for e in erreurs:
                print("  - " + e, file=sys.stderr)
            print("Corrige le fichier .env, puis relance.\n", file=sys.stderr)
            raise SystemExit(1)


# ---------------------------------------------------------- journalisation

def configurer_journalisation(app):
    """Écrit les journaux dans des fichiers avec rotation.

    Sans cela, en production derrière gunicorn, les erreurs partent dans la
    sortie standard et sont perdues — impossible de comprendre après coup
    pourquoi le site a échoué.
    """
    if not app.config["LOG_TO_FILE"]:
        return

    os.makedirs(app.config["LOG_DIR"], exist_ok=True)
    niveau = getattr(logging, app.config["LOG_LEVEL"].upper(), logging.INFO)

    format_journal = logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(module)s:%(lineno)d] %(message)s"
    )

    fichier = RotatingFileHandler(
        os.path.join(app.config["LOG_DIR"], "kaloum24.log"),
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )
    fichier.setFormatter(format_journal)
    fichier.setLevel(niveau)

    erreurs = RotatingFileHandler(
        os.path.join(app.config["LOG_DIR"], "erreurs.log"),
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )
    erreurs.setFormatter(format_journal)
    erreurs.setLevel(logging.ERROR)

    app.logger.addHandler(fichier)
    app.logger.addHandler(erreurs)
    app.logger.setLevel(niveau)
    app.logger.info("Journalisation fichier activée (%s)", app.config["LOG_DIR"])
