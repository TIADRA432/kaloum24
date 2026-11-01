# KALOUM24 V2 — Plan de tests et recette

Statut : tests définis, NON EXÉCUTÉS. Ne pas confondre ce document avec un rapport de réussite.

| ID | Contrôle | Critère attendu |
|---|---|---|
| T01 | Django system check, migrations sur base jetable | Aucun échec |
| T02 | Homepage, catégories, article, pagination, recherche | HTTP 200, contenu correct |
| T03 | Création brouillon, prévisualisation, validation, publication | Workflow et audit fonctionnels |
| T04 | Permissions journaliste / éditeur / admin | Aucun accès interdit |
| T05 | Mobile Android, 360px, réseau lent | Navigation et édition utilisables |
| T06 | Français et Pulaar | Unicode, URLs, affichage, recherche sans corruption |
| T07 | Images vers stockage persistant | Après redéploiement, fichiers toujours présents |
| T08 | SEO : canonical, Open Graph, NewsArticle, RSS, sitemap | Métadonnées et endpoints corrects |
| T09 | Commentaires modérés, signalements | Pas de publication sans modération |
| T10 | Abonnements / paywall / webhooks | Contrôles d'accès et idempotence |
| T11 | WhatsApp et agrégateur RSS | Brouillons sûrs, aucune autopublication |
| T12 | Import dry-run / import réel staging | Comptages et IDs cohérents, pas de doublons |
| T13 | Sauvegarde et restauration staging | Données et médias restaurés |
| T14 | Security checks, dépendances, CSRF, sessions | Pas de vulnérabilité bloquante connue |
| T15 | Performance mobile / Core Web Vitals | Mesures comparées à l'existant, seuils à fixer |
| T16 | Rollback staging | Retour à version précédente validé |

Automatisation prévue : CI GitHub Actions avec lint, tests Django, vérification migrations, scan dépendances; ne pas ajouter avant prototype exécutable.
