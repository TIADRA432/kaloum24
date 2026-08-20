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
