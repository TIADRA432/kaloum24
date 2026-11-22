#!/usr/bin/env bash
# Build Render : dépendances, statiques, migrations Supabase, structure du site.
# Les migrations sont dans le BUILD : un échec bloque le déploiement et l'ancienne
# version reste en ligne. Toutes les commandes sont idempotentes.
set -euo pipefail
pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py init_kaloum24
python manage.py seed_pulaar
python manage.py publier_articles || echo "publier_articles : échec ignoré, le site reste en ligne"
python manage.py importer_prix_pam || echo "importer_prix_pam : échec ignoré, le site reste en ligne"
python manage.py importer_change_bcrg || echo "importer_change_bcrg : échec ignoré, le site reste en ligne"
python manage.py verifier_dictionnaire || echo "verifier_dictionnaire : violations signalées (voir ci-dessus), le site reste en ligne"
