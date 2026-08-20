#!/usr/bin/env python3
"""Restaure une sauvegarde créée par sauvegarde.py.

Usage :
    python scripts/restaurer.py sauvegardes/kaloum24-20260808-030000.tar.gz

Écrase la base et les images actuelles — une copie de sécurité de l'état
existant est créée avant toute chose.
"""
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "instance", "kaloum24.db")
UPLOADS = os.path.join(BASE_DIR, "static", "uploads")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    archive = sys.argv[1]
    if not os.path.exists(archive):
        print(f"Archive introuvable : {archive}")
        return 1

    reponse = input("Cette opération écrase la base actuelle. Continuer ? (oui/non) ")
    if reponse.strip().lower() not in ("oui", "o", "yes", "y"):
        print("Annulé.")
        return 0

    horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
    if os.path.exists(DB_PATH):
        secours = f"{DB_PATH}.avant-restauration-{horodatage}"
        shutil.copy2(DB_PATH, secours)
        print(f"Copie de sécurité de l'état actuel : {secours}")

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(tmp)

        db_source = os.path.join(tmp, "kaloum24.db")
        if os.path.exists(db_source):
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            shutil.copy2(db_source, DB_PATH)
            print("Base restaurée.")

        uploads_source = os.path.join(tmp, "uploads")
        if os.path.isdir(uploads_source):
            os.makedirs(UPLOADS, exist_ok=True)
            for nom in os.listdir(uploads_source):
                shutil.copy2(os.path.join(uploads_source, nom), os.path.join(UPLOADS, nom))
            print("Images restaurées.")

    print("Restauration terminée.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
