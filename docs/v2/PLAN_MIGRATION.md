# KALOUM24 V2 — Plan de migration et rollback

Statut : planifié, non exécuté. Change ID : KALOUM24-CHANGE-002. Risque : élevé lors de la bascule, faible pour la documentation et branche isolée.

1. **Audit** : inventorier routes Flask, modèles SQLAlchemy, tables Alembic, permissions, fichiers, URLs et données réellement récupérables; établir matrice de parité.
2. **Sauvegarde** : vérifier exports base PostgreSQL, fichiers médias, variables non secrètes, configuration Render et commit/tag Flask. Tester une restauration dans un environnement isolé.
3. **Prototype** : générer Wagtail News Template dans `v2/` sur cette branche; figer versions Django/Wagtail/Python; aucun code Flask remplacé.
4. **Staging** : service Render distinct et base Supabase staging isolée; stockage médias objet; secrets uniquement dans les gestionnaires dédiés.
5. **Modélisation** : correspondance Article/Category/User/Comment/Subscription/Source/WhatsAppDraft vers nouveaux modèles. Scripts idempotents avec dry-run, journal et contrôle de cardinalité.
6. **Fonctionnalités** : reproduire workflow rédactionnel, SEO, commentaires, RSS, recherche, Pulaar, premium et intégrations; définir périmètre V2 minimal accepté.
7. **Tests** : unitaires, intégration, sécurité, accessibilité, mobile, charge, restauration, migration et liens historiques.
8. **Validation** : approbation explicite avant toute connexion aux données réelles ou bascule du trafic.
9. **Bascule** : gel éditorial court, sauvegarde finale, import, comparaison comptes/articles/médias, tests smoke, switch contrôlé.
10. **Rollback** : revenir au service Flask/commit précédent et au routage précédent; ne jamais supprimer anciennes données pendant la période de garantie. Éviter écriture simultanée dans deux bases non synchronisées.
11. **Documentation** : compte rendu des tests, changement, décision et rollback dans Confluence.

## Critères go/no-go
- Tous les articles récupérables, slugs, images, auteurs et dates conservés; redirections 301 pour URLs modifiées.
- Connexion rédaction et publication depuis Android, permissions par rôle, sauvegarde/restauration testée.
- Aucun secret exposé; pas de régression majeure SEO, commentaires, abonnements ou intégrations retenues.
- Validation du propriétaire éditorial et du prestataire technique avant production.

## État initial constaté
Application Flask 3, SQLAlchemy, Flask-Migrate, Jinja2. Render existant indisponible faute de base historique; projet Supabase créé mais non raccordé. La récupération des données historiques reste non garantie.
