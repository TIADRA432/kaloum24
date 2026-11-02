# KALOUM24 V2 — Plan de tests et recette

Statut : plan de recette. Les preuves obtenues sont dans `v2/VALIDATION.md` et
ne valident pas toutes les lignes ci-dessous. Les vérifications étendues sont
actuellement différées à la demande du propriétaire. L'aperçu ne valide pas la
publication, l'admin, la migration ou le rendu des vrais articles.

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
| T12 | Import dry-run / import réel explicitement autorisé | Comptages et IDs cohérents, pas de doublons ; aucun staging créé |
| T13 | Sauvegarde et restauration dans une destination locale temporaire approuvée | Données et médias restaurés ; production préservée |
| T14 | Security checks, dépendances, CSRF, sessions | Pas de vulnérabilité bloquante connue |
| T15 | Performance mobile / Core Web Vitals | Mesures comparées à l'existant, seuils à fixer |
| T16 | Rollback V2 dans le périmètre autorisé | Retour à version précédente validé ; V1 préservée |

La CI V2 existe pour les contrôles sans base, le bootstrap et la configuration.
Les tests nécessitant migrations ou écritures ne sont pas ajoutés implicitement.
L'aperçu utilise un backend de base factice et ne charge pas les secrets Supabase.
