# KALOUM24 V2 — Architecture cible (proposition)

Statut : conception, aucune bascule de production. Change ID : KALOUM24-CHANGE-002.

## Architecture
- Frontend : Django templates + Wagtail News Template, mobile-first, accessible, léger en données.
- Backend : Django LTS + Wagtail version compatible et verrouillée, éditorial Wagtail (pages, brouillons, workflows, révisions, permissions).
- Données : PostgreSQL Supabase dédié kaloum24-production, schéma V2 séparé ou base isolée de staging; aucune migration sur la base de production sans validation.
- Médias : stockage objet persistant (S3-compatible ou Supabase Storage), jamais disque éphémère Render.
- Déploiement : service Render distinct en staging, secrets en variables privées, Gunicorn, WhiteNoise pour statiques, HTTPS, healthcheck.
- SEO : conserver slugs, redirects 301, canonical, NewsArticle, Open Graph, sitemap, robots, RSS.
- Internationalisation : français principal, Pulaar testé (libellés, URLs, saisie Unicode, recherche, polices, lecture audio selon support).
- Métier : portage progressif des comptes, commentaires modérés, abonnements/paywall, Stripe webhooks, brouillons WhatsApp, agrégation RSS/Atom, statistiques, TTS.
- Observabilité : logs structurés sans secrets, erreurs applicatives, alertes, sauvegardes/restauration vérifiées.

## Découpage suggéré
- `config/` settings par environnement ; `news/` modèles de pages, rubriques, auteurs ; `accounts/` comptes et rôles ; `comments/` modération ; `subscriptions/` premium ; `integrations/` WhatsApp et RSS ; `locales/` traductions ; `tests/` tests automatisés.
- Le template Wagtail News est un starter, pas une application à intégrer par simple dépendance : générer la V2 dans un répertoire dédié `v2/` en gardant Flask intact.

## Invariants
Aucun changement DNS, Render, Supabase ou branche main. Aucun secret dans Git. Aucun import de comptes avec mots de passe en clair. Aucun contenu ancien inventé.
