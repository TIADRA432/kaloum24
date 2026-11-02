# KALOUM24 V2 — Plan de migration et rollback

Statut : socle et aperçu préparés ; migration et bascule non exécutées.
Change ID : KALOUM24-CHANGE-002. Aucun staging ne sera créé.
Suivi : [roadmap Confluence](https://joomwan.atlassian.net/wiki/spaces/TIADRA/pages/43483138/Kaloum24+V2+Roadmap+and+delivery+tracker).

1. **Audit** : inventorier routes Flask, modèles SQLAlchemy, tables Alembic, permissions, fichiers, URLs et données réellement récupérables; établir matrice de parité.
2. **Sauvegarde** : vérifier exports base PostgreSQL, fichiers médias, variables non secrètes, configuration Render et commit/tag Flask. Tester une restauration dans un environnement isolé.
3. **Prototype** : générer Wagtail News Template dans `v2/` sur cette branche; figer versions Django/Wagtail/Python; aucun code Flask remplacé.
4. **Préparation sans staging** : conserver Supabase existant et Render V1. Préparer les fichiers de déploiement V2 et le stockage médias objet sans créer de service ou de base. Utiliser l'aperçu local sans backend de base.
5. **Modélisation** : correspondance Article/Category/User/Comment/Subscription/Source/WhatsAppDraft vers nouveaux modèles. Scripts idempotents avec dry-run, journal et contrôle de cardinalité.
6. **Fonctionnalités** : reproduire workflow rédactionnel, SEO, commentaires, RSS, recherche, Pulaar, premium et intégrations; définir périmètre V2 minimal accepté.
7. **Recette planifiée** : unitaires, intégration, sécurité, accessibilité, mobile, charge, restauration, migration et liens historiques. Les vérifications étendues sont actuellement différées à la demande du propriétaire ; consigner les observations ciblées réellement obtenues.
8. **Validation** : connexion Supabase en lecture seule autorisée et opérationnelle. Sauvegarde vérifiée/restaurable et validation explicite avant migration, import ou écriture de contenu. Bascule de trafic approuvée séparément.
9. **Bascule** : gel éditorial court, sauvegarde finale, import, comparaison comptes/articles/médias, tests smoke, switch contrôlé.
10. **Rollback** : revenir au service Flask/commit précédent et au routage précédent; ne jamais supprimer anciennes données pendant la période de garantie. Éviter écriture simultanée dans deux bases non synchronisées.
11. **Documentation** : compte rendu des tests, changement, décision et rollback dans Confluence.

## Critères go/no-go
- Tous les articles récupérables, slugs, images, auteurs et dates conservés; redirections 301 pour URLs modifiées.
- Connexion rédaction et publication depuis Android, permissions par rôle, sauvegarde/restauration testée.
- Aucun secret exposé; pas de régression majeure SEO, commentaires, abonnements ou intégrations retenues.
- Validation du propriétaire éditorial et du prestataire technique avant production.

## État initial constaté
Application historique Flask 3, SQLAlchemy, Flask-Migrate, Jinja2. Sa disponibilité
et la récupération historique ne sont pas réévaluées dans ce lot. La connexion
Django au Supabase existant fonctionne en lecture seule ; le schéma Wagtail n'a
pas été installé. La récupération des contenus historiques reste non garantie.
