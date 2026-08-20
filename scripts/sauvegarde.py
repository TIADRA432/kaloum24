#!/usr/bin/env python3
"""Sauvegarde la base de données et les images envoyées.

Usage :
    python scripts/sauvegarde.py [dossier_destination]

Crée une archive horodatée contenant la base SQLite et le dossier des uploads,
puis supprime les sauvegardes de plus de 30 jours.

Pour une sauvegarde quotidienne automatique, ajouter dans la crontab :
    0 3 * * * cd /chemin/vers/kaloum24 && venv/bin/python scripts/sauvegarde.py
"""
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "instance", "kaloum24.db")
UPLOADS = os.path.join(BASE_DIR, "static", "uploads")
RETENTION_JOURS = 30


def copie_sqlite_coherente(source, destination):
    """Copie la base même pendant que le site tourne.

    Un simple `cp` sur une base SQLite en cours d'écriture peut produire un
    fichier corrompu. L'API de sauvegarde de SQLite garantit un instantané
    cohérent.
    """
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst = sqlite3.connect(destination)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def main():
    destination = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "sauvegardes")
    os.makedirs(destination, exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Base introuvable : {DB_PATH}")
        return 1

    horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = os.path.join(destination, f"kaloum24-{horodatage}.tar.gz")

    with tempfile.TemporaryDirectory() as tmp:
        db_temp = os.path.join(tmp, "kaloum24.db")
        copie_sqlite_coherente(DB_PATH, db_temp)

        with tarfile.open(archive, "w:gz") as tar:
            tar.add(db_temp, arcname="kaloum24.db")
            if os.path.isdir(UPLOADS):
                tar.add(UPLOADS, arcname="uploads")

    taille = os.path.getsize(archive) / (1024 * 1024)
    print(f"Sauvegarde créée : {archive} ({taille:.1f} Mo)")

    # Purge des archives trop anciennes
    limite = datetime.now() - timedelta(days=RETENTION_JOURS)
    supprimees = 0
    for nom in os.listdir(destination):
        if not nom.startswith("kaloum24-") or not nom.endswith(".tar.gz"):
            continue
        chemin = os.path.join(destination, nom)
        if datetime.fromtimestamp(os.path.getmtime(chemin)) < limite:
            os.remove(chemin)
            supprimees += 1
    if supprimees:
        print(f"{supprimees} sauvegarde(s) de plus de {RETENTION_JOURS} jours supprimée(s).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
