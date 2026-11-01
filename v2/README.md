# Kaloum24 V2 — Wagtail News Template

**Phase 1 : bootstrap reproductible en environnement isolé.** Le projet Flask existant reste à la racine et n'est pas modifié.

Ce répertoire héberge le protocole de génération du site Wagtail officiel. Le code source du template n'a pas encore été copié dans le dépôt. La génération doit se faire dans `v2/site/` sur un environnement de développement ou une CI, jamais sur le service Render Flask.

## Prérequis
- Python 3.12/3.13 et accès réseau GitHub/PyPI
- Git, espace de travail isolé
- Aucun identifiant Supabase production nécessaire

## Démarrage
```bash
cd v2
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'wagtail>=7.0,<8.0'
python bootstrap_v2.py
cd site
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py test
```

L'outil utilise le template officiel Wagtail News depuis GitHub. Ne pas lancer `bootstrap.py` du template en environnement connecté à la production : ce script peut charger des données et des comptes de démonstration. Générer un superutilisateur uniquement avec un secret fort et dans l'environnement isolé.

## Portes de validation
1. Vérifier le commit exact du template, sa licence BSD-3, les versions Python/Django/Wagtail avant de figer le lockfile.
2. Exécuter les tests, vérifier les écrans publics et l'admin Android.
3. Configurer PostgreSQL staging, stockage objet, CI et les modules métier avant tout déploiement.
4. Faire approuver la migration de production séparément.

## État
Script de bootstrap et CI préparés; **génération et tests réels non exécutés à ce stade**.
