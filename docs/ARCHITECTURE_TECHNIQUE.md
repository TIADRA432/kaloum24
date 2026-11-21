# Kaloum24 V2 — Architecture technique

> Référence technique de la V2 (Wagtail/Django). Aucun secret ici : les valeurs vivent dans Render. Dernière mise à jour : 2026-11-21.

## 1. Vue d'ensemble

```
Lecteur ─► Render (web service gratuit, Francfort)
             gunicorn (2 workers, timeout 25 s, preload, max_requests 1200)
             └─ Django 6.0 + Wagtail 7.4 (+ WhiteNoise pour les statiques)
                 ├─ PostgreSQL 17 : Supabase « kaloum24-production » (Paris)
                 └─ Médias : bucket public « media » de Supabase Storage (API S3)
Rédaction ─► /admin/ (Wagtail)        Santé : /healthz
```

Environnements : production (`settings.render`), local (`dev`), tests (`test`, SQLite mémoire), CI (`ci`).

## 2. Pile logicielle (v2/site/requirements.txt)

| Composant | Version | Rôle |
|---|---|---|
| Python | 3.13 (seule version testée) | exécution |
| Django | 6.0.x | framework |
| Wagtail | 7.4.x | CMS (modèle « news-template » figé) |
| gunicorn | 23.0 | serveur WSGI |
| WhiteNoise | 6.12 | statiques compressés |
| dj-database-url | 3.1 | lecture de `DATABASE_URL` |
| psycopg[binary] | 3.3 | pilote PostgreSQL |
| django-storages[s3] + wagtail-storages | 1.14 / 2.0 | médias sur Supabase Storage |
| Front | Tailwind + webpack (`static_src`, `static_compiled`) | CSS/JS du thème |

## 3. Applications Django (`v2/site/kaloum24_v2/`)

| App | Contenu |
|---|---|
| `home` | `HomePage` (introduction, CTA, StoryBlock, pages liées) |
| `news` | `ArticlePage` (auteur, rubrique, date, lieu, chapô, image, corps `ArticleBody`, sources, temps de lecture), `NewsListingPage`, flux RSS `/news/feed/`, commande `publier_articles`, données `news/data/articles/*.json` |
| `standardpages` | `StandardPage`, `IndexPage` |
| `navigation` | `NavigationSettings` (menu principal et pied de page) |
| `utils` | blocs (`utils/blocks/`), snippets `AuthorSnippet` et `ArticleTopic`, mixins `SocialFields`/`ListingFields`, commande `init_kaloum24`, rôles et workflow |
| `pulaar` | dictionnaire : `PulaarDomain`, `PulaarSource`, `PulaarTerm`, `PulaarDefinition`, `PulaarProposal` ; `i18n.py`, `slug.py`, sitemap propre, commande `seed_pulaar`, charte `.tc` |
| `search` | recherche du site `/search/` |
| `forms`, `images`, `users` | formulaires Wagtail, modèle d'image, `User(AbstractUser)` |
| `public` | aperçu hérité et `/healthz` |

Apps Wagtail activées : settings, forms, redirects, sitemaps, table_block, search_promotions, embeds, sites, users, snippets, documents, images, search, admin ; plus modelcluster, taggit, `django.contrib.postgres` (production).

## 4. Routes principales

`/` accueil · `/actualites/` liste · `/actualites/<slug>/` article · `/pulaar/` dictionnaire · `/search/` · `/news/feed/` · `/sitemap.xml` (pages + Pulaar) · `/robots.txt` · `/healthz` · `/admin/` (Wagtail) · `/django-admin/` · `/documents/`.

## 5. Réglages et variables d'environnement (noms seulement)

Module : `DJANGO_SETTINGS_MODULE=kaloum24_v2.settings.render` en production.

| Variable | Rôle | Secret ? |
|---|---|---|
| `SECRET_KEY` | clé Django (obligatoire) | **oui** |
| `DATABASE_URL` | base Supabase | **oui** |
| `DATABASE_SSLMODE` | défaut `require` | non |
| `SITE_URL` / `RENDER_EXTERNAL_URL` / `RENDER_EXTERNAL_HOSTNAME` / `ALLOWED_HOSTS` | domaines | non |
| `SECURE_HSTS_SECONDS` | défaut 3600 | non |
| `SEO_NOINDEX` | `false` = indexation ouverte | non |
| `PYTHON_VERSION` | 3.13.x | non |
| `ADMIN_USERNAME`, `ADMIN_EMAIL` | compte admin initial | non |
| `ADMIN_PASSWORD` | à **retirer** après première connexion | **oui** |
| `AWS_*` (clés, bucket, endpoint, région) | S3 Supabase Storage | **oui** (clés) |
| `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | courriel (défaut `redaction@kaloum24.com`) | mot de passe : **oui** |

Règle : les secrets sont saisis par le propriétaire dans le tableau de bord Render, jamais dans une conversation, un commit ou une page de documentation.

## 6. Commandes de gestion (toutes idempotentes)

| Commande | Effet |
|---|---|
| `init_kaloum24` | structure : accueil, arborescence, rubriques, rôles (Rédacteurs, Relecteurs, Lexicographes Pulaar), workflow, image par défaut, compte admin |
| `seed_pulaar` | domaines, sources et termes initiaux du dictionnaire |
| `publier_articles` | publie les articles de `news/data/articles/*.json` **une seule fois** (révision `kaloum24.import`), redirection 301 si le slug change |

## 7. Construction et déploiement

`v2/site/build.sh` : `pip install` → `collectstatic` → `migrate` → `init_kaloum24` → `seed_pulaar` → `publier_articles || echo "échec ignoré"`. Une migration qui échoue bloque le déploiement : l'ancienne version reste en ligne.

Render : service `kaloum24` (`srv-dc0e0je7bikc73f8sokg`), branche `feat/kaloum24-v2-render`. Le déploiement automatique est peu fiable : utiliser `trigger_deploy` (MCP Render) puis vérifier `/healthz`, `/`, `/actualites/`. Plan gratuit : veille (démarrage à froid ~50 s).

## 8. Tests et CI

- Local : `cd v2/site && DJANGO_SETTINGS_MODULE=kaloum24_v2.settings.test python manage.py test kaloum24_v2` (33 tests au dernier relevé) puis `makemigrations --check --dry-run`.
- CI `.github/workflows/wagtail-v2.yml` : `pip check` → tests → migrations à jour → build complet sur PostgreSQL 17 éphémère. `graphify.yml` : graphe de code (V1).
- Un changement n'est « fait » que s'il est testé, déployé **et** vérifié en production.

## 9. Base de données et sécurité

- Supabase `kaloum24-production` (réf. `qlkeieckyhvpjmyzuwjk`), 74 tables, RLS activée partout + déclencheur `kaloum24_auto_rls` pour les futures tables ; aucune politique = aucun accès REST (voulu). Django se connecte avec le rôle propriétaire.
- Pooler Supabase : `prepare_threshold=None` requis.
- Sauvegardes : **aucune automatique exploitable** → export `pg_dump` régulier hors Supabase à mettre en place (sprint S0).
- Après chaque `migrate` créant des tables : vérifier `get_advisors` (sécurité).
- Médias : bucket `media` public, 10 Mo, images et PDF seulement, fichiers avec extension obligatoire.

## 10. Conventions de code

1. Aucun contenu inventé ; provenance des données ; « IA ≠ autorité linguistique ».
2. Charte Tiadra confinée à `/pulaar/` (`.tc`, `--tc-*`).
3. Nouveau champ ou modèle : migration versionnée, test associé, `makemigrations --check` propre.
4. Nouvelle fonctionnalité = nouvelle app `kaloum24_v2/<nom>` (ex. `prix`, `communaute`), ajoutée à `INSTALLED_APPS`, avec ses tests, sans toucher aux apps existantes plus que nécessaire.
5. Tout ce qui est rendu à l'utilisateur est en français d'abord ; le Pulaar n'est ajouté que fourni par un locuteur.
6. Respect des données personnelles (loi L/2016/037/AN) : minimum collecté, pas d'opinions politiques stockées sans nécessité.

## 11. Pièges connus

Voir `HANDOFF_AGENT.md` §6 (PostgreSQL + `django.contrib.postgres`, `settings.test` pour les statiques, Python 3.13 seulement, pooler Supabase, `create_web_service` sans `rootDir`, 403 au push si l'app GitHub n'est pas installée, `HomePage` par défaut renommée).

## 12. Cartographie des évolutions prévues

| Chantier | Nouvelle app / zone touchée |
|---|---|
| S1 accueil + brèves | `home`, `news` (type Brève) |
| S2 revue de presse | nouvelle app `revue` (RSS, extrait ≤ 400 car. + lien) |
| P1–P4 Baromètre des prix | nouvelle app `prix` |
| C1 commentaires et comptes | nouvelle app `communaute` |
| C2 forum | `communaute` (sections, sujets, messages) |
| Météo, lecture vocale, multilingue | `home`/widgets, `news` (champ « version audio »), `i18n` |

Détail et ordre : `PLAN_EVOLUTION.md` §5 bis.
