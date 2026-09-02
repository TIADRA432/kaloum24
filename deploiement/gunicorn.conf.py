"""Configuration gunicorn pour Kaloum24.

Lancement :
    gunicorn -c deploiement/gunicorn.conf.py "app:app"
"""
import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")

# Règle usuelle : 2 × cœurs + 1. Sur un petit VPS (1 vCPU), 3 workers suffisent.
# ATTENTION : avec plusieurs workers et SQLite, les écritures se sérialisent.
# Au-delà de quelques workers, passe à PostgreSQL.
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Threads par worker : utile car l'application attend souvent des entrées/sorties
# (base de données, API météo, API WhatsApp).
threads = int(os.environ.get("GUNICORN_THREADS", "2"))

worker_class = "gthread"
timeout = 60
graceful_timeout = 30
keepalive = 5

# Redémarrage périodique des workers : évite qu'une fuite mémoire lente ne
# finisse par saturer le serveur. Le jitter décale les redémarrages pour ne
# pas les faire tous en même temps.
max_requests = 1000
max_requests_jitter = 100

accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Journalise la vraie IP du visiteur (transmise par Nginx) et non celle du proxy.
access_log_format = '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sµs'

preload_app = False   # doit rester False : chaque worker a son propre tampon de vues


def on_starting(server):
    """S'exécute une seule fois, avant que le moindre worker ne démarre —
    jamais une fois par worker. Sert à créer l'administrateur de démarrage
    (flask bootstrap-admin) sur un hébergeur où la commande de démarrage
    n'est configurable qu'à la création du service (Render, notamment) :
    plutôt que de dépendre de cette commande externe, cette étape vit ici,
    dans du code versionné et déployé avec le reste du projet.

    Idempotent par construction (voir app.py, bootstrap-admin) : ne fait
    rien si les variables ADMIN_* sont absentes ou si le compte existe déjà.
    """
    import subprocess
    try:
        resultat = subprocess.run(
            ["flask", "bootstrap-admin"],
            capture_output=True, text=True, timeout=30,
        )
        for ligne in (resultat.stdout + resultat.stderr).splitlines():
            server.log.info("bootstrap-admin: %s", ligne)
    except Exception as exc:
        server.log.warning("bootstrap-admin : n'a pas pu s'exécuter (%s) — "
                           "sans conséquence si un admin existe déjà.", exc)

    # Même principe : flask seed-pulaar est idempotent (vérifié — voir
    # seed_pulaar.py, PLAN_PULAAR.md §G) et pas d'accès shell direct sur
    # Render pour le lancer manuellement une seule fois.
    try:
        resultat = subprocess.run(
            ["flask", "seed-pulaar"],
            capture_output=True, text=True, timeout=30,
        )
        for ligne in (resultat.stdout + resultat.stderr).splitlines():
            server.log.info("seed-pulaar: %s", ligne)
    except Exception as exc:
        server.log.warning("seed-pulaar : n'a pas pu s'exécuter (%s) — "
                           "sans conséquence si déjà amorcé.", exc)

    # Rattrape les slugs créés avant la correction de slugify() (consonnes
    # pulaar supprimées au lieu d'être translittérées). Idempotent : ne fait
    # rien une fois tous les slugs corrects.
    try:
        resultat = subprocess.run(
            ["flask", "corriger-slugs-pulaar"],
            capture_output=True, text=True, timeout=30,
        )
        for ligne in (resultat.stdout + resultat.stderr).splitlines():
            server.log.info("corriger-slugs-pulaar: %s", ligne)
    except Exception as exc:
        server.log.warning("corriger-slugs-pulaar : n'a pas pu s'exécuter (%s).", exc)
