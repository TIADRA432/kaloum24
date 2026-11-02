# KALOUM24 V2 — Architecture cible (proposition)

Statut : socle opérationnel et interface locale ; aucune bascule de production.
Change ID : KALOUM24-CHANGE-002. Actualisé au 2 novembre 2026.
Suivi : [roadmap Confluence](https://joomwan.atlassian.net/wiki/spaces/TIADRA/pages/43483138/Kaloum24+V2+Roadmap+and+delivery+tracker).

## Architecture
- Frontend : Django templates + Wagtail News Template, mobile-first, accessible, léger en données.
- Backend : Django 6.0.7 et Wagtail 7.4.2 du starter figé ; pages, brouillons, workflows, révisions et permissions. Verrouillage complet des dépendances à terminer avant déploiement.
- Données : Supabase existant `qlkeieckyhvpjmyzuwjk` / `kaloum24-production`, en lecture seule. Aucun projet ou branche de staging. La destination du schéma V2 et ses conflits potentiels seront revus avant migration.
- Médias : stockage objet persistant (S3-compatible ou Supabase Storage), jamais disque éphémère Render.
- Déploiement : aucun service créé. Préparer un service V2 distinct lorsque son déploiement sera autorisé ; ne pas modifier Render Flask V1. Secrets privés, Gunicorn, WhiteNoise, HTTPS et healthcheck seront requis.
- SEO : conserver slugs, redirects 301, canonical, NewsArticle, Open Graph, sitemap, robots, RSS.
- Internationalisation : français principal, Pulaar testé (libellés, URLs, saisie Unicode, recherche, polices, lecture audio selon support).
- Métier : portage progressif des comptes, commentaires modérés, abonnements/paywall, Stripe webhooks, brouillons WhatsApp, agrégation RSS/Atom, statistiques, TTS.
- Observabilité : logs structurés sans secrets, erreurs applicatives, alertes, sauvegardes/restauration vérifiées.

## Découpage suggéré
- `config/` settings par environnement ; `news/` modèles de pages, rubriques, auteurs ; `accounts/` comptes et rôles ; `comments/` modération ; `subscriptions/` premium ; `integrations/` WhatsApp et RSS ; `locales/` traductions ; `tests/` tests automatisés.
- Le template Wagtail News est un starter, pas une application à intégrer par simple dépendance : générer la V2 dans un répertoire dédié `v2/` en gardant Flask intact.

## Invariants
Aucun changement DNS, Render Flask V1 ou branche `main`. Aucun secret dans Git.
Les réglages Supabase déjà autorisés sont l'obligation SSL, Temporary Access et
le mapping temporaire du propriétaire. Aucune migration ni écriture de contenu
sans sauvegarde vérifiée/restaurable et validation explicite. Aucun import de
comptes avec mots de passe en clair. Aucun contenu ancien inventé.

## Organisation du code réellement livré

- `v2/site/` : starter généré et ignoré par Git.
- `v2/config/` : settings suivis ; Supabase en lecture seule et aperçu sans base.
- `v2/overrides/` : vues, URLs, template français et CSS spécifiques à Kaloum24.
- `v2/apply_overrides.py` : applique ces sources au starter, sans SQL.
- `v2/preview_v2.py` : aperçu sur localhost avec backend de base factice ; aucun identifiant Supabase chargé.
- `/healthz` : vie du processus uniquement, aucune promesse de disponibilité du schéma éditorial.
