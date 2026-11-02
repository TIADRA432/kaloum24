# Validation Kaloum24 V2 — 2 novembre 2026 (UTC)

## Périmètre et références

- Branche : `feat/kaloum24-django-wagtail-v2`, parent initial
  `3f563e6bfab6845c1c7259b972329a3c62b21cb4`.
- `main` initial : `1a898e8c6f365920df1c968cefe9d74e5f2f5907`.
- [Échec Actions reproduit dans les logs](https://github.com/TIADRA432/kaloum24/actions/runs/41325494536) :
  `No module named wagtail.__main__` à la génération.
- Template officiel figé : `3758d56f2c31413bdb1b2aaa96cb7b9e8e150ad9`.

## Résultats locaux

Windows, Python 3.13.4, environnement dédié `v2/.venv` :

| Vérification | Résultat |
| --- | --- |
| `python -m unittest discover -s tests -v` depuis `v2` | 10 tests réussis, aucune connexion |
| `python bootstrap_v2.py` | Génération réelle réussie dans `v2/site`, aucune migration |
| Installation des dépendances du template | Réussie |
| `python -m pip check` | Aucune dépendance cassée |
| `python site/manage.py check --settings=kaloum24_v2.settings.ci` | Code 0, huit avertissements Treebeard |
| Même check avec `settings.supabase`, URL et secret factices | Code 0, huit avertissements, sans connexion à la base |
| Trois tests upstream de `utils.tests.test_blocks` via `unittest` après `django.setup()` | 3 réussis ; `SimpleTestCase`, aucun runner de base |
| `python -m compileall -q site/kaloum24_v2` | Réussi |

Les avertissements `treebeard.E001` annoncent une incompatibilité future des
managers Wagtail avec Treebeard 6. La version installée est 5.3.1 et Wagtail
impose `<6` ; les avertissements ne sont pas supprimés.

## Résultats GitHub Actions

Commit correctif : [`9fae4f952336dad68b8538bb9f847a2c6b0bd47a`](https://github.com/TIADRA432/kaloum24/commit/9fae4f952336dad68b8538bb9f847a2c6b0bd47a).

- [Workflow V2 réussi](https://github.com/TIADRA432/kaloum24/actions/runs/41514543094) :
  Linux Python 3.12 et 3.13, chacun avec 10 tests de régression et 3 tests
  upstream réussis, génération réelle, dépendances et checks validés.
  Huit avertissements Treebeard par check, aucune erreur.
- [Workflow existant Graphify réussi](https://github.com/TIADRA432/kaloum24/actions/runs/41514543063) :
  graphe construit et **512/512 tests V1 réussis**. Il a été déclenché
  automatiquement par le push et n'a pas été modifié. Ces tests existants
  utilisent des données et bases temporaires isolées, sans secret Supabase.
- `main` vérifié après publication : toujours
  `1a898e8c6f365920df1c968cefe9d74e5f2f5907`.
- Copie locale alignée sur le commit publié ; seuls les fichiers `v2/**` et
  `.github/workflows/wagtail-v2-bootstrap.yml` diffèrent du parent initial.

## Supabase : observation réelle en lecture seule

Projet existant `qlkeieckyhvpjmyzuwjk`, nom `kaloum24-production`, région
`eu-west-3`, état `ACTIVE_HEALTHY`.

Requête exécutée via le connecteur MCP : `BEGIN TRANSACTION READ ONLY`, SELECT
sur les métadonnées puis `ROLLBACK`.

```json
{"database":"postgres","read_only":"on","postgres_version":"17.11","ssl":true,"tls_version":"TLSv1.3","public_table_count":0,"wagtail_table_count":0,"django_migrations_present":false}
```

Les comptes de tables sont limités aux objets visibles par le rôle MCP. Aucun
contenu applicatif n'a été consulté ni modifié. Cette observation valide le
chemin MCP, pas une connexion Django/psycopg locale : aucun `DATABASE_URL`
authentifié n'est fourni dans l'environnement local. La sonde locale est testée
avec connexions simulées ; le test réseau direct reste à réaliser avec un secret
fourni par un canal sécurisé.

## Limites et suite autorisée

Aucun staging, aucune migration ni écriture sur Supabase, aucun changement
Render. La validation V2 n'a créé ni migré de base de test et n'a chargé ni
fixtures, utilisateur ou rôle en base. Seuls `v2/**` et le workflow V2 sont
modifiés. Les tests upstream nécessitant des écritures n'ont pas été exécutés ;
la suite V1 a été exécutée automatiquement dans sa CI isolée préexistante.

1. Fournir de manière sécurisée l'URL PostgreSQL du projet existant et exécuter
   `python check_supabase_readonly.py` ; vérifier éventuellement `verify-full`
   avec le certificat CA Supabase.
2. Avant tout changement en base : sauvegarde vérifiée/restaurable, inventaire
   des schémas et revue du plan de migration, puis validation explicite.
3. Après cette validation seulement : installation du schéma, tests applicatifs
   complets et vérifications publiques/admin ; aucun déploiement V1 implicite.
4. Verrouiller les dépendances transitives avant un déploiement V2.

## Préparation de Temporary Access — 2 novembre 2026 (UTC)

- Connexion directe avec le mot de passe local : refus d'authentification par
  Supabase, avant toute requête SQL applicative. Aucun secret n'est consigné.
- Contrôle MCP supplémentaire : base `postgres`, transaction `read_only=on`,
  SSL actif et TLS 1.3 ; ce chemin existant reste fonctionnel.
- Ajout de `DATABASE_AUTH_MODE=access_token` et `SUPABASE_ACCESS_TOKEN` : token
  injecté en mémoire, destination limitée au projet existant, `jit=on` ajouté
  uniquement pour le pooler, lecture seule et SSL conservés.
- Ajout d'un GET du statut JIT et du chargement explicite d'un fichier `.env`.
- **18 tests locaux réussis**, sans connexion réseau/base. Le check Django avec
  mode PAT et token factice réussit avec les huit avertissements connus.
- Tableau de bord inspecté : aucune commande Temporary Access visible dans
  Database Settings pour ce projet. Le statut réel doit donc être lu via l'API
  de gestion après fourniture du PAT ; il n'est pas présumé activé ou désactivé.
- Formulaire de création préparé, pas soumis : `kaloum24-v2-temporary-check`,
  expiration 24 heures, seul projet `qlkeieckyhvpjmyzuwjk`, **Project Settings:
  Read** et **Database JIT: Read**. Aucun token créé pendant cette préparation.
- L'activation JIT, les autorisations de rôle et la connexion réelle par PAT
  restent à valider ; aucune écriture Supabase ni modification Render effectuée.

## Vérification réelle du PAT — 2 novembre 2026 (UTC)

- Token fourni localement par l'utilisateur ; aucune valeur secrète affichée,
  ajoutée aux commits ou transmise dans une URL.
- GET du projet avec ce token : **HTTP 200**, projet cible confirmé et état
  `ACTIVE_HEALTHY`. Le PAT et son périmètre Project Settings Read fonctionnent.
- Le guide Temporary Access indiquait `/database/jit-access` (HTTP 404).
  La [référence API](https://supabase.com/docs/reference/api/v1-get-jit-access-config)
  donne le chemin effectif `/jit-access` : checker et test corrigés.
- Réponse réelle du statut, sans secret :

```json
{"temporary_access_state":"unavailable","unavailable_reason":"ssl_enforcement_required"}
```

- Le GET des autorisations `/database/jit` répond HTTP 406 dans cet état.
  Aucune autorisation de rôle ne peut être conclue à partir de ce résultat.
- La sonde PostgreSQL directe par PAT n'a pas été lancée après ce constat.
- Métadonnées de connexions lues via MCP, dans une transaction READ ONLY puis
  ROLLBACK : quatre sessions TLS et une session sans TLS du moniteur interne
  `postgres_exporter`. Ce relevé ponctuel ne garantit pas la compatibilité de
  tous les clients existants ou déconnectés.
- Selon la [documentation SSL](https://supabase.com/docs/guides/platform/ssl-enforcement),
  activer l'obligation SSL entraîne un redémarrage de la base et une interruption
  possible. Ce changement de production n'a pas été appliqué ; il nécessite une
  validation et un créneau approprié. Aucun mot de passe réinitialisé, aucune
  migration ni écriture Supabase effectuée.
- Le checker traite désormais `unavailable`, conserve les appels GET seuls et
  n'affiche qu'une raison connue ; les raisons inconnues restent masquées.
- **20 tests locaux réussis** ; la commande réelle de statut retourne le motif
  SSL attendu avec le token local, sans tentative d'activation.
