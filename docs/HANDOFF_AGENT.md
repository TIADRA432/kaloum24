# Kaloum24 — Passation pour un agent IA

> À lire en entier avant de toucher au code. Aucun secret dans ce fichier : ne jamais en ajouter.
> Dernière mise à jour : 2026-11-22 (branche `feat/kaloum24-v2-render`).

## 1. Le projet en une page

Kaloum24 est un portail d'actualités guinéen, en français, avec un dictionnaire Pulaar. Propriétaire : **Samba (Abdourahmane Barry)**, Conakry, qui écrit en français, par messages courts (« continue », « go »). Réponds en français, franchement, sans enrobage. Son cycle de travail : **planifier → construire → tester → déployer → vérifier en conditions réelles**. Il attend du concret opérationnel, pas des plans.

Deux générations de code coexistent :

| | V1 (Flask) | **V2 (Wagtail/Django) — la cible** |
|---|---|---|
| Emplacement | racine du dépôt (`app.py`, `blueprints/`, `models.py`…) | `v2/site/` |
| Branche | `main` (dernier commit utile `c2e9430` + audit Graphify `1a898e8`) | `feat/kaloum24-v2-render` |
| État | **hors service** : sa base Render a expiré | à déployer |
| À faire | ne plus développer ; sert de référence fonctionnelle | tout le développement |

Les autres branches : `fix/core-stabilisation` (durcissement Flask, non fusionné), `feature/pulaar-santa-maria` (brouillon éditorial bilingue), `chore/kaloum24-db-recovery-20261031` (plan de reprise après perte de base), `codex/graphify-audit`, `feat/kaloum24-django-wagtail-v2` (prototype lecture seule, remplacé).

## 2. Stack V2

Python 3.13 · Django 6.0 · Wagtail 7.4 (modèle « news-template » officiel figé) · PostgreSQL 17 **Supabase** (projet `kaloum24-production`, réf. `qlkeieckyhvpjmyzuwjk`, Paris) · WhiteNoise · gunicorn · Render (web service gratuit, Francfort).

Applications (`v2/site/kaloum24_v2/`) : `home`, `news` (ArticlePage, NewsListingPage), `standardpages`, `navigation`, `utils` (blocs, snippets Auteur/Rubrique, commande `init_kaloum24`), **`pulaar`** (dictionnaire), `search`, `forms`, `images`, `users`, `public` (aperçu hérité + `/healthz`).

Réglages : `settings/base.py` (commun) · `dev.py` · `test.py` (SQLite mémoire, sans manifeste statique) · `ci.py` · **`render.py` (production)**. `settings/local.py` est ignoré par git (usage personnel).

## 3. Commandes

```bash
cd v2/site
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=kaloum24_v2.settings.test
python manage.py test kaloum24_v2            # 33 tests, aucun secret, aucune base externe
python manage.py makemigrations --check --dry-run
```
Local complet : `settings.dev` + `python manage.py createcachetable migrate init_kaloum24 seed_pulaar` puis `runserver`. Sur PostgreSQL local, ajouter `django.contrib.postgres` (voir §6).

`build.sh` (utilisé par Render) : pip install → collectstatic → **migrate** → `init_kaloum24` → `seed_pulaar`. Tout est idempotent. Les migrations sont dans le build : un échec bloque le déploiement, l'ancienne version reste en ligne.

## 4. Déploiement Render + Supabase

Variables d'environnement (jamais dans le code ni dans le chat) :

| Variable | Rôle |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `kaloum24_v2.settings.render` |
| `SECRET_KEY` | obligatoire, générée par Render |
| `DATABASE_URL` | chaîne **Session pooler** de Supabase (port **5432**, hôte `*.pooler.supabase.com`, utilisateur `postgres.<réf>`). Pas le port 6543, pas l'hôte direct IPv6 |
| `SITE_URL` | ex. `https://kaloum24.onrender.com` |
| `PYTHON_VERSION` | `3.13.5` (testé en 3.13) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` | créent le premier superutilisateur **seulement s'il n'en existe aucun**. Retirer `ADMIN_PASSWORD` après le premier déploiement |
| `AWS_*` (bucket, clés, endpoint, région, domaine personnalisé) | médias persistants via l'interface S3 de Supabase Storage |
| `EMAIL_HOST`… | notifications de workflow (sinon console) |

Commandes Render : build `cd v2/site && ./build.sh` · start `cd v2/site && gunicorn kaloum24_v2.wsgi --config gunicorn.conf.py --bind 0.0.0.0:$PORT` · health check `/healthz` (sans SQL, exempté de la redirection HTTPS).

**Le disque de Render est éphémère** : sans les variables `AWS_*`, toute image envoyée disparaît au redéploiement. Supabase ne gère pas les ACL S3 : bucket public en lecture, `AWS_S3_CUSTOM_DOMAIN=<réf>.supabase.co/storage/v1/object/public/<bucket>`.

Plan gratuit : le service s'endort (démarrage à froid ~50 s) ; un projet Supabase gratuit se met en pause après une semaine d'inactivité et n'a pas de sauvegarde automatique exploitable. **C'est exactement ainsi que la première base a été perdue** (la base Render gratuite expire). Prévoir un export régulier (`pg_dump`) hors de Supabase.

Sécurité Supabase à faire après le premier `migrate` : activer **RLS** sur toutes les tables du schéma `public` (Supabase les expose via PostgREST ; Django se connecte avec le rôle propriétaire et n'est pas affecté), puis vérifier `get_advisors`. SSL est déjà imposé sur le projet.

## 5. Conventions non négociables

1. **Aucun contenu inventé** : pas d'article factice, pas de statistique, pas de traduction pulaar approximative. `init_kaloum24` ne crée que la structure.
2. **« IA ≠ autorité linguistique »** : un texte pulaar généré par IA n'est jamais présenté comme valide. Les traductions de l'interface (`pulaar/i18n.py`) viennent de la localisation fulah officielle de Firefox (7/15) ; le reste reste en français tant qu'un locuteur n'a pas fourni les chaînes.
3. **Provenance obligatoire** : chaque terme a une source (`PROTECT`). Une proposition validée devient « documenté », jamais « validé » (acte de linguiste distinct).
4. **Licences** (agrégateur, V1) : extrait ≤ 400 caractères + lien pour les médias ; texte intégral seulement pour des sources institutionnelles avec justification. Pas de contournement de CAPTCHA, d'authentification ou d'anti-bot.
5. **Charte Tiadra Consortium** (bordeaux #5D2E38, or #D19F5E, Roboto Slab 700 / Montserrat) : cantonnée à `/pulaar/` (classe `.tc`, variables `--tc-*`). Ne pas l'étendre au reste du site ni aux e-mails existants.
6. Ne rien détruire sans migration validée ; ne jamais committer de secret ; ne pas réutiliser le projet Supabase `le-jacquier-restaurant` (autre client).
7. Consonnes ɓ ɗ ŋ ƴ : vraies lettres. `slug.py` les translittère (`ɗ→d`) ; la recherche tolère un clavier sans ces lettres.

## 6. Pièges déjà rencontrés

- Sur PostgreSQL, Wagtail exige `django.contrib.postgres` dans `INSTALLED_APPS` (déjà dans `render.py`).
- Tests avec `ManifestStaticFilesStorage` : utiliser `settings.test` (stockage statique simple).
- Les dépendances ont des roues Python 3.14, mais seul 3.13 a été testé : garder `PYTHON_VERSION`.
- Le pooler Supabase ignore `default_transaction_read_only` en options de démarrage ; `prepare_threshold=None` est requis.
- `create_web_service` (outil Render) n'a pas de `rootDir` : on passe par `cd v2/site &&`. Il n'existe pas d'outil pour modifier un service existant (branche/commandes) : le faire au dashboard ou recréer le service.
- `git push` depuis la session IA exige l'application GitHub Claude installée sur l'organisation, sinon 403.
- Wagtail rend une `HomePage` par défaut à la migration : `init_kaloum24` la renomme au lieu d'en créer une autre.
- Anciennes erreurs V1 utiles : un `server_default` est requis pour tout nouveau champ NOT NULL ; avec Alembic, découvrir les noms de contraintes à l'exécution.

- **Polices** (constaté 2026-11-21) : Source Serif 4 / Source Sans 3 sont déclarées dans `tailwind.config.js` mais **jamais chargées** (seul Source Code Pro a des `@font-face`) ; aucune police du site ne contient ɓ ɗ ŋ ƴ. Voir `docs/CHARTE_GRAPHIQUE.md` (S0b, 3 directions en attente de choix).

## 7. Éditorial (Wagtail)

Mis à jour le 2026-11-21. Le corps d'un article (`ArticleBody`, `utils/blocks/article.py`) est une suite de blocs de presse : paragraphe, intertitre, citation, image (légende + crédit), encadré, tableau, vidéo/embed ; les anciens blocs `section`, `cta`, `statistics` restent valides. Champs d'article : lieu (`dateline`), chapô, sources, temps de lecture calculé. Mise en page de lecture : `news/static/news/article.css` (préfixe `.art-`, couleurs héritées du thème). `wagtail.embeds` et `wagtail.contrib.table_block` sont installés.

Rôles (`init_kaloum24`, `_roles`) : les groupes Wagtail d'origine sont **renommés** une seule fois — `Editors` → **Rédacteurs** (ajouter/modifier sous « Actualités », soumettre) et `Moderators` → **Relecteurs** (+ publier, verrouiller) — et leurs droits sur la racine sont retirés. Workflow « Relecture éditoriale ». Les droits ajustés ensuite par un administrateur ne sont jamais réécrits. Groupe supplémentaire **Lexicographes Pulaar**. Rubriques = snippets `ArticleTopic`. Signature par défaut « Rédaction Kaloum24 ». Guide pour l'équipe : `docs/GUIDE_REDACTION_WAGTAIL.md`. Dictionnaire : menu « Dictionnaire Pulaar » (valider une proposition publie le terme, « documenté »).

Import d'articles versionné (`publier_articles`, appelé par `build.sh`, non bloquant) : lit `news/data/articles/*.json` (titre, slug, `ancien_slug`, rubrique, signature, chapô, blocs) et publie une révision marquée `kaloum24.import`. **Une seule fois par article** : si cette entrée existe dans l'historique, la commande ne touche plus à la page (le travail des rédacteurs n'est jamais écrasé). Si le slug change, une redirection 301 depuis l'ancien est créée. Premier article : « Alkule latin potndinaaɗe » (rubrique Pulaar, page 5, `/actualites/alkule-latin-potndinaade-no-pular-winndirtee/`, 18 blocs dont un tableau des voyelles, ancienne adresse redirigée en 301 — vérifié en production le 2026-11-21). Réserves : texte Pulaar fourni tel quel, non validé par un locuteur (IA ≠ autorité linguistique) ; affirmations UNESCO (Bamako 1966, Niamey 1978) sans source (champ Sources vide).

## 8. État au 2026-11-20 et reste à faire (par priorité)

**En ligne** : service Render `kaloum24` (id `srv-dc0e0je7bikc73f8sokg`, branche `feat/kaloum24-v2-render`, https://kaloum24.onrender.com ; l'ancien service Flask a été supprimé et le service provisoire `kaloum24-wagtail` doit l'être aussi), base Supabase migrée (74 tables), `init_kaloum24` et `seed_pulaar` exécutés, `/`, `/actualites/`, `/pulaar/`, `/admin/login/`, `/healthz` répondent 200, indexation ouverte (`SEO_NOINDEX=false`), `robots.txt` et `sitemap.xml` en place (à déclarer dans Google Search Console). Le déploiement automatique sur push ne se déclenche pas toujours : utiliser `trigger_deploy`.
**RLS** : activée sur les 74 tables (migration `enable_rls_on_all_public_tables`) + déclencheur d'événement `kaloum24_auto_rls` qui l'active sur les futures tables. L'avertissement Supabase « RLS enabled, no policy » (INFO) est voulu : aucun accès via l'API REST.

1. Connexion admin à vérifier par le propriétaire (compte `samba`), puis supprimer `ADMIN_PASSWORD` de Render. Health check à régler sur `/healthz` au dashboard.
2. Export de sauvegarde planifié (`pg_dump`) hors de Supabase.
3. ~~Médias persistants~~ **Fait** (2026-11-20) : bucket public `media` (10 Mo max, images + PDF) sur Supabase Storage via S3, variables `AWS_*` posées sur Render ; vérifié (image envoyée par l'admin présente dans `storage.objects`). Piège : le bucket refuse les fichiers sans extension (`InvalidMimeType`) ; `init_kaloum24` restaure l'image par défaut `original_images/placeholder-image.webp` si son fichier a disparu.
4. Changer le mot de passe admin, retirer `ADMIN_PASSWORD`, **renouveler tous les secrets déjà vus en conversation** (ancienne `SECRET_KEY`, ancien mot de passe admin, ancien jeton GitHub, ancien mot de passe de base).
5. Parité V1 à décider avec le propriétaire : commentaires, agrégateur RSS (`collector.py`, `scoring_engine.py`), publication programmée (Wagtail le fait nativement), Stripe, WhatsApp/Meta, newsletter (non fonctionnelle en V1).
6. Pulaar : plus de définitions monolingues (0/22 aujourd'hui) ; un locuteur doit fournir les 8 chaînes d'interface manquantes (dictionnaire, définition, domaine, proposer un mot, tous les termes, documenté, validé, source).
7. Courriels de demande d'autorisation (rédigés, à envoyer par le propriétaire) : DiLAF/LS2N (Chantal Enguehard, univ-nantes.fr) et SIL Dictionaries & Lexicography ; le consentement d'Oumar Bah est nécessaire pour son *Dictionnaire Pular* (Webonary, non libre de droits).
8. L'audit Graphify (`docs/AUDIT_GRAPHIFY.md`) liste des défauts V1 non corrigés (XSS dans l'aperçu RSS admin, CSRF des paiements, CSP Facebook…) : ne concernent la V2 que si ces fonctions sont reportées.

## 8 ter. Avancement du backlog

| Item | État | Détail |
|---|---|---|
| S0 Cadre | **fait** (2026-11-21, vérifié en production) | 11 rubriques ; brouillons non publiés « Charte éditoriale », « Mentions légales », « À propos » (champs `[À COMPLÉTER]` : statut légal, directeur de publication, contacts — rien d'inventé). À publier par le propriétaire après compléments et avis d'un juriste. |
| S1 Accueil vivant | **fait, sauf 3 points** (2026-11-21) | Accueil : à la une, flash info (snippet `Breve`, menu admin « Brèves »), dernières nouvelles, blocs par rubrique, mot du jour Pulaar (`pulaar.models.mot_du_jour`, rotation quotidienne, source affichée). CSS `home/accueil.css` (préfixe `.acc-`, pas de recompilation Tailwind). Reste : (1) **sauvegarde** : workflow `.github/workflows/sauvegarde-base.yml` écrit mais **non exécuté** — il attend les secrets GitHub `SUPABASE_DB_URL` et `BACKUP_PASSPHRASE` saisis par le propriétaire ; le dépôt étant **public**, l'archive n'est pas conservée tant qu'il n'est pas privé ou qu'un stockage privé n'est pas branché ; (2) droits des groupes Rédacteurs/Relecteurs sur « Brèves » à accorder dans l'admin ; (3) images WebP / chargement différé et lien des pages cadre dans le pied de page, à faire à leur publication. |

| S1b Site vivant | **fait** (2026-11-21) | Barre d'info sur toutes les pages sauf `/pulaar/` (charte Tiadra à part) : date/heure de Conakry (JS, `home/vie.js`), flash info défilant (brèves en ligne, puis titres des derniers articles ; message neutre si rien), météo Conakry ; bloc météo 7 villes sur l'accueil ; logo qui scintille ; apparitions douces. CSS `home/vie.css` ; tout est neutralisé par `prefers-reduced-motion`. Météo : `home/meteo.py`, **MET Norway** (User-Agent identifiant obligatoire, cache 3 h, secours 24 h, jamais d'erreur 500). Piège : Open-Meteo renvoie 429 depuis Render. Balise : `{% bandeau_vivant %}` dans `base_page.html`. |
| S0b Identité visuelle | **fait en grande partie** (2026-11-21) | Indigo/ocre, Unbounded + Charis SIL auto-hébergées (lettres guinéennes OK), accueil immersif (`home/immersif.css/js`), tokens `home/k24.css`. Reste : listes par rubrique, `/pulaar/`, Safari, ambiances par page (voir `CHARTE_GRAPHIQUE.md`). |
| S2 Revue de presse | **fait** (2026-11-21) | `news/presse.py` : modèles `SourcePresse` / `ArticlePresse`, flux RSS publics, extrait ≤ 400 car. + lien, titre + source, jamais le texte complet. Collecte « paresseuse » (visite, toutes les 30 min, en arrière-plan) + commande `collecter_presse`. Page `/revue-de-presse/`, bloc d'accueil. 9 sources actives (Guinéenews, Mosaïque, Guinée360, Vision Guinée, Guinée Matin, Le Jour Guinée, Le Révélateur 224, Fouta Ka Meen, Kumpital) + **RFI Fulfulde** activée à la demande du propriétaire (2026-11-21 ; conditions de réutilisation RFI non confirmées ; titres en fulfulde jamais traduits, badge « Fulfulde » + `lang="ff"`, champ `SourcePresse.langue`). **Écartées** : Africaguinee et Ledjely (403 : on ne contourne pas), RFI Afrique désactivée, Primature « actualités en pular » (flux de commentaires vide), Pulaaku.bj (radio, pas de flux), VOA Fulfulde (flux introuvable). Un média peut demander son retrait : décocher « actif » dans l'admin. |
| S2b Images | **fait** (2026-11-21) | Miniatures de la revue (`ArticlePresse.image`, hotlink + crédit « Image : média », option `SourcePresse.images`) ; si le flux n'a pas d'image, `og:image` de la page (nouveaux titres seulement, 8 pages max/collecte). Photos libres Wikimedia Commons (CC BY-SA) + `credits.json`, page `/credits-images/`, tag `{% illustrations %}`. La mosaïque « La Guinée en images » (`components/guinee-images.html`) a été **retirée de l'accueil** à la demande du propriétaire (pas d'images près du header) : à replacer ailleurs. Pictogrammes de produits dessinés (`icone_produit`, SVG maison) sur les chiffres du jour et `/prix/`. Les 6 photos de référence du propriétaire ne sont **pas utilisées** (droits inconnus : demander la source). |
| S1c Météo monde peul | **fait** (2026-11-21) | 18 villes (Guinée, Sénégal, Mali, Côte d'Ivoire, Ghana, Burkina, Nigéria, Cameroun, Centrafrique) dans `home/meteo.py` (nom, lat, lon, pays ; cache `meteo:v3`). |
| S3 Météo | **fait** (2026-11-21) | Page `/meteo/` : 18 villes regroupées par pays (`home/views.py::meteo_page`, même service/cache que l'accueil, panne = message, jamais d'erreur 500). Lien dans le pied de page. |
| L Convertisseur | **fait** (2026-11-21) | `/convertisseur/` (`prix/change.py`, modèle `TauxChange`, commande `importer_change_bcrg` dans `build.sh`, non bloquante). Source : **cours de référence BCRG** (PDF quotidien « Devises contre GNF ») dont l'adresse vient de l'API WordPress publique `bcrg-guinee.org/wp-json/wp/v2/cours_des_devises` ; lecture par `pypdf` ; **seules les adresses `bcrg-guinee.org/wp-content/uploads/` sont suivies** ; tentative horaire en arrière-plan ; en cas d'échec on garde le dernier cours daté. 12 devises dont XOF (XAF = même valeur). Le format des PDF varie (`USD 8 650,97` ou `8839.0137USD`) : `analyser()` gère les deux ; un PDF sans USD/EUR est refusé. Cours **indicatif** (ni marché parallèle ni bureaux de change). Pas encore fait : carburant, dollar au marché parallèle (pas de source officielle). |
| S7 Distribution | **fait sauf newsletter** (2026-11-21/22) | (1) Aperçu de partage : balises OpenGraph/Twitter/canonique dans `base_page.html` (blocs `og_title`, `og_type`, `og_description` surchargeables ; image = `social_image` > `listing_image` > `home/partage.jpg` 1200×630, 92 Ko). Les pages hors CMS (revue, prix, météo, convertisseur…) définissent `og_title`. (2) Boutons de partage sous les articles (`components/partage.html` : WhatsApp, Facebook, copie du lien ; aucun traqueur). (3) Flux RSS par rubrique `/news/feed/<slug>/` (**`<str:slug>` et non `<slug:>`** : les slugs de rubriques sont accentués — « économie », « régions » ; bug 500 corrigé) + page `/flux-rss/`. (4) PWA : `/manifest.webmanifest`, `/sw.js` (racine, `Cache-Control: no-cache`, cache versionné par `RENDER_GIT_COMMIT`), `/hors-ligne/` ; jamais en cache : `/admin/`, `/django-admin/`, `/search/`, `/documents/` ; 40 pages max ; icônes `home/static/home/icones/` (médaillon indigo/ocre, remplacent celles du gabarit). Vérifié en production avec Playwright (SW actif, page vue lisible hors ligne, page inconnue → « hors ligne »). **Reste** : newsletter (décision du propriétaire : service d'envoi, stockage des abonnés, consentement) ; test d'installation sur téléphone par le propriétaire. |

**À venir, demandé par le propriétaire (2026-11-21)** : **S0b Charte graphique** (PLAN_EVOLUTION §5 ter ; état et 3 directions : `docs/CHARTE_GRAPHIQUE.md`), à faire avant tout nouveau chantier visuel. Les couleurs et polices actuelles viennent du gabarit Wagtail ; le rouge du flash info (`#c8102e`) est provisoire.

## 8 bis. Chantiers en cours (verrous)

Ajouter une ligne avant de commencer, la retirer à la fin (voir `AGENTS.md` §6).

| Item backlog | Branche | Qui | Depuis | Déploiement en cours ? |
|---|---|---|---|---|
| _(aucun)_ | | | | |

## 9. Documents

**Confluence** (miroir de lecture, espace personnel de Samba, page racine « Kaloum24 » : planning, décisions et risques, technique, charte agents, runbooks, volets produit). Le dépôt fait foi.

**Entrée agents** : `AGENTS.md` (règles, rôles, cycle, collaboration). **Technique** : `docs/ARCHITECTURE_TECHNIQUE.md`.

**Planification** : `docs/PLAN_EVOLUTION.md` (étude des références, propositions, backlog priorisé et sprints S0–S8) `docs/PLAN_OBSERVATOIRE_PRIX.md` (volet Prix, P1–P4) et `docs/PLAN_COMMUNAUTE.md` (commentaires, comptes, forum : C1–C3). Ce sont les documents de pilotage : suivre l'ordre du backlog (§5 bis), un sprint à la fois.

`docs/v2/` (architecture, plan de migration, plan de tests, feuille de route : historique du prototype), `PLAN_PULAAR.md`, `PLAN_REDACTION.md`, `GUIDE_REDACTION.md`, `docs/RECOVERY_RENDER_DATABASE_2026-10-31.md` (sur sa branche), catalogue de ressources Pulaar (`catalogue_ressources_pulaar.md`).
