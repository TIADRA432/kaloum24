# KALOUM24 — Plan de reprise après expiration de la base Render

- ID : KALOUM24-CHANGE-001
- Date : 2026-10-31
- Responsable technique : prestataire technique
- Statut : audit en cours — aucune modification de production
- Risque : critique (perte potentielle de données éditoriales)

## État initial vérifié
- Application Flask 3, Flask-SQLAlchemy, Flask-Migrate (Alembic).
- SQLite par défaut ; configuration DATABASE_URL accepte PostgreSQL, normalise postgres:// en postgresql://.
- Pilote psycopg2-binary déjà déclaré dans requirements.txt.
- Modèles relationnels : utilisateurs, articles, catégories, commentaires, abonnements, etc.
- L'état et les sauvegardes Render n'ont pas encore pu être inspectés ; aucune perte définitive de données n'est confirmée.
- Un audit précédent mentionne des problèmes de sécurité non résolus : voir docs/AUDIT_INITIAL.md.

## Décision d'architecture
Conserver Flask et SQLAlchemy ; privilégier PostgreSQL managé pour la production. Firebase Firestore exigerait une réécriture du modèle de persistance et n'est pas recommandé pour cette restauration. Créer un projet Supabase dédié (ne pas réutiliser la base du restaurant Le Jacquier).

## Procédure de reprise (à exécuter après accès Render)
1. Identifier le service Render et la base associée ; relever le type (Postgres/SQLite), le statut, la date d'expiration et les possibilités de récupération, sans publier de secrets.
2. Vérifier snapshots, sauvegardes automatiques, exports SQL, volumes/disques persistants, stockage objet des images, fichiers .db et archives locales.
3. Si PostgreSQL récupérable : exporter avec pg_dump au format custom ; conserver une copie chiffrée hors Render ; vérifier restauration sur une base de test.
4. Si SQLite récupérable : sauvegarder le fichier .db avec méthode cohérente, vérifier integrity_check et faire une migration contrôlée vers PostgreSQL.
5. Si aucune donnée récupérable : établir un inventaire de ce qui manque, initialiser une base PostgreSQL neuve avec flask db upgrade ; ne pas exécuter seed-db en production.
6. Créer une base PostgreSQL dédiée ; secrets DATABASE_URL uniquement dans les variables d'environnement Render ; SSL et compatibilité pooler/psycopg2 à vérifier.
7. Tester les migrations sur staging : schéma, clés étrangères, comptes, authentification, articles, commentaires, module pulaar, upload d'images, abonnements.
8. Vérifier restauration et sauvegardes planifiées, puis déployer en production avec plan de retour arrière.
9. Valider le site sur mobile et desktop ; documenter le résultat et le point de restauration.

## Précautions
- Ne jamais exécuter de migration destructive sur l'unique copie.
- Ne pas utiliser la base du restaurant existant pour Kaloum24.
- Ne pas exposer la connexion Postgres dans GitHub, logs, navigateur ou frontend.
- Les images stockées dans static/uploads sur disque éphémère doivent être auditées séparément.
- Réparer les problèmes de sécurité identifiés avant réouverture complète des fonctions sensibles.

## Rollback
Conserver le service/configuration actuelle et la sauvegarde pré-migration ; restaurer la DATABASE_URL précédente et la version de code correspondante uniquement si la base précédente est encore disponible. Sinon restaurer le snapshot testé de PostgreSQL sur une base dédiée, puis repointer l'application.

## Résultat
Audit de code effectué. Inspection de l'hébergement Render et récupération des données en attente de connexion Render. Aucune modification de production ni création de base.
