# Kaloum24 V2 — Wagtail News Template

Le bootstrap génère le site dans `v2/site/` (ignoré par Git). La V1 Flask,
`main` et la configuration Render existante ne sont pas modifiés. Aucun staging
n'est créé. Le seul projet Supabase visé est `qlkeieckyhvpjmyzuwjk`.

## Suivi du projet

Le suivi des étapes est publié dans [Confluence — Roadmap Kaloum24 V2](https://joomwan.atlassian.net/wiki/spaces/TIADRA/pages/43483138/Kaloum24+V2+Roadmap+and+delivery+tracker).

## Aperçu public et édition locale

Après génération du starter et installation de ses dépendances :

```bash
cd v2
# Utiliser l'interpréteur de .venv (ou activer cet environnement).
python preview_v2.py
```

Ouvrir `http://127.0.0.1:8782/`. Ce serveur est limité à localhost ; il utilise
un backend de base factice, ne charge pas `.env`, n'exécute aucune migration et
ne lit ni n'écrit Supabase. Le rendu est français, avec rubriques, formulaire de
recherche et états vides. Aucun article ou historique n'est inventé. Les flux
éditoriaux réels restent à brancher après installation du schéma autorisée.

Les sources à modifier sont suivies dans `v2/overrides/`, et les settings dans
`v2/config/`. Les modifications directes de `v2/site/` resteraient ignorées par Git.

```bash
python apply_overrides.py
```

Après cette commande, rafraîchir le navigateur pour les changements HTML/CSS.
Redémarrer l'aperçu après une modification Python ou des settings. Le bootstrap
applique aussi ces fichiers automatiquement lors d'une nouvelle génération.
L'URL Wagtail générée conserve ses routes admin, recherche et RSS et ajoute
`/healthz`, un endpoint de vie sans requête SQL. L'aperçu sert aussi `/healthz`
et un `robots.txt` qui interdit l'indexation. Aucun déploiement public n'est réalisé.

## Bootstrap reproductible

Python 3.12 ou 3.13, accès GitHub/PyPI, environnement sans `DATABASE_URL`,
`PGHOST` ni `PGSERVICE` :

```bash
cd v2
python -m venv .venv
# Linux/macOS : source .venv/bin/activate
# PowerShell : .venv/Scripts/Activate.ps1
python -m pip install -r requirements-bootstrap.txt
python -m unittest discover -s tests -v
python bootstrap_v2.py
python -m pip install -r site/requirements.txt
python -m pip check
python site/manage.py check --settings=kaloum24_v2.settings.ci
python -m compileall -q site/kaloum24_v2
```

La commande officielle est `wagtail start --template=<archive> <nom> <destination>`.
Le script appelle son point d'entrée avec **le même interpréteur Python** :

```bash
python -m wagtail.bin.wagtail start --template=https://github.com/wagtail/news-template/archive/3758d56f2c31413bdb1b2aaa96cb7b9e8e150ad9.zip kaloum24_v2 site
```

Cette commande manuelle suppose que `site` existe déjà et est vide. Notre script
le crée puis refuse tout écrasement. `python -m wagtail` échoue car Wagtail n'a
pas de `__main__.py`. L'aide correcte est `python -m wagtail.bin.wagtail help start`.

Template figé au commit `3758d56f2c31413bdb1b2aaa96cb7b9e8e150ad9`, licence BSD-3.
Dépendances principales : Django 6.0.7, Wagtail 7.4.2, dj-database-url 3.1.2,
psycopg 3.3.4. Les dépendances transitives ne constituent pas encore un lockfile
complet ; un verrouillage sera requis avant déploiement.

Ne pas exécuter le `bootstrap.py` généré : il lance des migrations, crée un cache
en base et peut charger du contenu et un administrateur de démonstration.
Le bootstrap V2 fait uniquement de la génération de fichiers et copie les
configurations de `config/` dans `site/kaloum24_v2/settings/`.
Après modification des configurations, les recopier ou régénérer le site après
avoir conservé les éventuelles modifications locales ; il n'est jamais écrasé.

## PostgreSQL existant, SSL et lecture seule

Voir `.env.example` pour les noms de variables, sans identifiants réels.
Les fichiers `.env` ne sont pas chargés automatiquement. Fournir les valeurs par
l'environnement, via un gestionnaire de secrets, sans les committer ni les
insérer dans une commande enregistrée dans l'historique.

- `DATABASE_URL` : URL PostgreSQL complète ; encoder les caractères spéciaux du mot de passe.
- `DATABASE_SSLMODE` : `require` par défaut ; `verify-full` avec le certificat CA
  Supabase pour vérifier aussi le certificat et le nom d'hôte. `require` chiffre
  le transport sans garantir cette vérification du nom d'hôte.
- `DATABASE_SSLROOTCERT` : chemin du certificat pour `verify-ca` / `verify-full`.
- `SECRET_KEY`, `ALLOWED_HOSTS` : requis pour les settings `supabase`.

Copier l'URL exacte dans le panneau **Connect** du projet existant. La connexion
directe `db.qlkeieckyhvpjmyzuwjk.supabase.co:5432` exige généralement IPv6 ; pour
un réseau IPv4, utiliser le **Session pooler**, port 5432, utilisateur
`postgres.qlkeieckyhvpjmyzuwjk`, avec l'hôte fourni par Supabase. Ne pas inventer
l'hôte du pooler. Les curseurs serveur et les prepared statements sont désactivés.
L'inspection Django exige le port 5432 (direct ou Session pooler) ; le pooler
transactionnel 6543 est refusé car la protection en lecture seule utilise une
configuration de session.

La configuration refuse SQLite, les modes SSL faibles et les paramètres URL
arbitraires. Elle impose `default_transaction_read_only=on`, une connexion de
10 secondes et un délai SQL de 10 secondes. Après connexion, un hook Django
impose `SET default_transaction_read_only = on` et ferme la connexion si cette
protection n'est pas active : le pooler ignore ce réglage dans les options de
démarrage. Le cache Django reste en mémoire.
Ces paramètres protègent l'inspection ; un rôle PostgreSQL dédié en lecture
seule reste préférable à un compte administrateur. Aucun rôle n'est créé ici.

Après génération, un contrôle de configuration sans connexion est possible :

```bash
python site/manage.py check --settings=kaloum24_v2.settings.supabase
```

Pour une vérification réseau réelle, après fourniture sécurisée de `DATABASE_URL` :

```bash
python check_supabase_readonly.py
```

La sonde vérifie le projet cible, impose une transaction en lecture seule,
interroge uniquement les métadonnées PostgreSQL/TLS puis fait `ROLLBACK`, y
compris en cas d'échec SQL. Aucun contenu d'article ni secret n'est affiché.
Le contrôle du nombre de tables reflète uniquement les tables visibles au rôle.
Le connecteur MCP Supabase a été testé séparément ; il ne fournit pas le mot de
passe nécessaire à une connexion Django/psycopg locale.

## Alternative : Personal Access Token et Temporary Access

La connexion au tableau de bord avec GitHub reste utilisable. Supabase propose
[Temporary Access](https://supabase.com/docs/guides/platform/temporary-access)
pour authentifier une connexion PostgreSQL avec un Personal Access Token (PAT).
Il faut d'abord que cette fonctionnalité soit activée sur le projet et que
l'utilisateur soit autorisé à utiliser le rôle PostgreSQL choisi. Le PAT ne
remplace pas ces autorisations et conserve les permissions du rôle assumé.
Les clés API de projet `anon`, `service_role`, publishable ou secret ne sont
pas des PAT.

Dans l'environnement local, ou le fichier `.env` ignoré par Git :

```dotenv
DATABASE_AUTH_MODE=access_token
SUPABASE_ACCESS_TOKEN=<PAT à saisir localement uniquement>
```

Conserver l'URL du projet existant. Le champ mot de passe peut être retiré de
l'URL : le PAT est injecté en mémoire, sans être journalisé. Pour le pooler,
`-c jit=true` est ajouté automatiquement aux options, en conservant SSL, le mode
lecture seule et les délais. Aucun autre paramètre SQL arbitraire n'est accepté.
Le pooler exige la chaîne littérale `true` ; `jit=on` provenant de l'ancien
exemple est normalisé en `jit=true`. Voir le
[parseur Supavisor](https://github.com/supabase/supavisor/blob/3829f69b78ed254be2444ccb5f86f8a100a4bc0c/lib/supavisor/client_handler/protocol_helpers.ex#L79).

La sonde et la commande de statut peuvent lire explicitement le fichier local :

```bash
cd v2
python check_supabase_access.py --env-file .env
python check_supabase_readonly.py --env-file .env
```

La première commande fait uniquement un GET du statut Temporary Access via
l'API de gestion. Elle exige un PAT avec **Project Settings: Read** sur le seul
projet `qlkeieckyhvpjmyzuwjk`. **Database JIT: Read** permet aussi l'inspection
des autorisations JIT. Préférer un PAT limité à ce projet et de courte durée
(24 heures pour le contrôle initial), sans droits de migration ou d'écriture.

Le statut est lu sur `GET /v1/projects/{ref}/jit-access`, conformément à la
[référence API](https://supabase.com/docs/reference/api/v1-get-jit-access-config).
Le chemin `/database/jit-access` du guide général renvoie 404 sur le projet.
La commande accepte aussi `unavailable` et rapporte la raison connue
`ssl_enforcement_required`. Dans ce cas, l'activation de l'obligation SSL est
un préalable. Cette modification provoque un redémarrage de la base et peut
interrompre les connexions ; elle doit être examinée et autorisée séparément.
Voir la [documentation SSL](https://supabase.com/docs/guides/platform/ssl-enforcement).

Si le statut est `disabled`, `unavailable` ou si aucun rôle n'est autorisé, la connexion
PostgreSQL n'est pas encore utilisable. L'activation et les autorisations JIT
nécessitent une modification d'accès séparée, examinée avant application.
Ces scripts n'activent rien, ne créent aucun rôle et ne changent aucun mot de
passe. Le PAT d'inspection préparé ne possède pas ces droits de modification.
Le paramètre de lecture seule du client ne remplace pas une restriction du rôle
PostgreSQL lui-même. Voir aussi les [permissions PAT](https://supabase.com/docs/guides/platform/personal-access-tokens).

## Tests et étapes suivantes

La CI vérifie Python 3.12 et 3.13, les régressions du bootstrap/configuration,
la génération réelle, les dépendances, les checks Django et trois tests upstream
`SimpleTestCase`, exécutés via `unittest` sans création de base ni migrations.
Elle ne reçoit aucun secret Supabase. Les tests upstream nécessitant une base
ne sont pas lancés. Le workflow Graphify préexistant lance automatiquement les
tests Flask V1 dans des bases temporaires isolées ; ce workflow reste inchangé.
Voir [le rapport de validation](VALIDATION.md) pour les résultats et liens Actions.

Les huit avertissements `treebeard.E001` constatés avec treebeard 5.3.1 concernent
les managers Wagtail et une future incompatibilité avec Treebeard 6 ; Wagtail
contraint actuellement cette dépendance à `<6`. Ils ne sont pas masqués.

Avant toute migration ou écriture : obtenir une sauvegarde vérifiée/restaurable
du projet existant, préparer et relire le plan SQL, vérifier les conflits de
schémas et obtenir une validation explicite. Puis seulement réaliser la phase
autorisée. L'admin et le rendu public complet ne sont pas validés tant que le
schéma V2 n'est pas installé. Aucun déploiement n'est effectué ici.

Sources : [template officiel](https://github.com/wagtail/news-template/tree/3758d56f2c31413bdb1b2aaa96cb7b9e8e150ad9),
[point d'entrée Wagtail](https://github.com/wagtail/wagtail/blob/v7.4.2/wagtail/bin/wagtail.py),
[connexions Supabase et SSL](https://supabase.com/docs/guides/database/connecting-to-postgres).
