# Kaloum24 — Communauté : comptes lecteurs, commentaires, forum

> Conception du 2026-11-21. **Rien n'est construit.** Le backlog unifié est dans `PLAN_EVOLUTION.md` §5 bis.
> Règles : modération avant tout, aucune donnée personnelle inutile, aucun secret dans le code.

## 1. Ce que vous voulez

1. Les lecteurs **commentent** les articles, avec ou sans compte.
2. Un **compte lecteur** facultatif (nom d'utilisateur, mot de passe) pour interagir plus.
3. Un **forum** à la Nairaland : sections et sous-sections, sujets liés aux articles, zones de discussion.
4. Un **blog par utilisateur** : jugé lourd, donc écarté pour l'instant (voir §7).

## 2. Ce que fait Nairaland (référence)

Forum fondé en 2005 par Seun Osewa, financé par la publicité bannière. D'après les descriptions publiques : structure **hiérarchique de sections et de sous-forums** (politique, éducation, emploi…), équipe de **modérateurs**, points de réputation, règles contre le trolling, la désinformation et la haine, interface sobre et rapide pour mobile. Deux leçons :
- La **structure claire par sections** est ce qui le rend utilisable (et la section Emploi y est l'une des plus fréquentées).
- La **modération insuffisante est son talon d'achille** : la presse l'a critiqué pour cela, et <cite index="317-1">Cloudflare l'a un jour coupé pour abus non précisés</cite>. Un forum non modéré met le site entier en danger.

## 3. Architecture proposée, en trois paliers

**Palier C1 — Commentaires et comptes lecteurs (priorité haute)**
- Commentaires sous chaque article, **modérés avant affichage au début** (file d'attente), puis allégés pour les comptes de confiance.
- **Deux modes** : invité (pseudo + commentaire, avec anti-spam) ou compte (pseudo + mot de passe + e-mail pour la récupération). Un compte donne : historique, notifications de réponse, réactions, abonnement à des rubriques.
- **Réactions rapides** : « Pertinent / Utile / À débattre ».
- Réponses imbriquées sur un seul niveau (lisible sur petit écran).
- **Signaler** un commentaire ; **liste de mots bloqués** ; limites de fréquence ; **possibilité de fermer les commentaires** d'un article sensible.
- Connexion simple et légère ; option plus tard d'une connexion par numéro de téléphone (coût SMS à budgéter).

**Palier C2 — Forum (après C1 et une communauté qui existe)**
- Structure : **Sections → sous-sections → sujets → messages**, avec épinglage, verrouillage, déplacement, recherche.
- **Sujet lié à un article** (bouton « Discuter dans le forum »).
- Sections de départ proposées (à valider) : Actualité & débats, Économie & prix (lien avec le Baromètre), Emploi & formation, Langues & culture (Pulaar, Maninka, Soussou, Wolof…), Technologie, Diaspora, Vie pratique, Suggestions pour le site.
- Rôles : membre, membre de confiance, modérateur par section, administrateur.
- Réputation modeste (nombre de messages utiles), pas de classements publics au début.

**Palier C3 — Blogs (non planifié)** : voir §7.

## 4. Choix technique (à trancher au démarrage du palier)

| Option | Pour | Contre |
|---|---|---|
| **A. Intégré à Kaloum24 (Django)** : modèles et vues maintenus par nous, ou module de forum Django | Un seul site, un seul compte, un seul hébergement, pages légères, modération dans l'admin Wagtail | Plus de code à maintenir ; django-machina est un moteur de forum conçu pour s'intégrer à une application Django (licence BSD), mais **sa compatibilité avec Django 6 / Wagtail 7.4 n'est pas vérifiée** |
| **B. Discourse séparé** (sous-domaine) | Très complet (niveaux de confiance, notifications) | Exige Docker, PostgreSQL et Redis, **au moins 1 Go de RAM**, un serveur payant, connexion unique à configurer ; ne tourne pas sur l'offre gratuite de Render |
| **C. Service tiers** (commentaires hébergés) | Rapide | Données hors de notre contrôle, pages plus lourdes, dépendance |

**Recommandation** : **A** pour C1 (modèle de commentaires et comptes simples, en s'appuyant sur une bibliothèque d'authentification Django reconnue) ; pour C2, **évaluer d'abord** un module de forum Django compatible avec nos versions, sinon construire un forum minimal (sections, sujets, messages, modération). **B** seulement si la communauté grandit beaucoup et qu'un budget d'hébergement existe.

## 5. Cadre légal, données personnelles, modération

- **Loi guinéenne L/2016/037/AN** (cybersécurité et protection des données personnelles) : <cite index="340-1">les données sensibles comprennent les données relatives aux opinions ou activités religieuses, philosophiques, politiques, syndicales</cite>. Or un forum de discussion révèle des opinions : **ne collecter que le strict nécessaire** (pseudo, e-mail), pas de nom réel ni de numéro obligatoire, politique de confidentialité publiée, suppression de compte possible. L'organisme de protection prévu par la loi n'a pas de voie de plainte publique localisée (source secondaire) ; **validation juridique requise**.
- **Responsabilité éditoriale** : la HAC a prévenu que les web médias fautifs relèveraient de la loi sur la cybersécurité. Un site qui héberge des commentaires est exposé aux contenus diffamatoires ou haineux : **modération préalable au début, charte de la communauté, procédure de retrait rapide, journal des décisions**.
- **Conservation minimale** : adresse IP et e-mail conservés le moins longtemps possible, accessibles à peu de personnes ; durée à fixer avec le juriste.
- **Contenus interdits** : diffamation, haine, appels à la violence, données personnelles d'autrui, publicité sauvage. Section « Annonces » séparée si besoin.
- **Rumeurs et sécurité** : pas de section politique non modérée ; sujets sensibles modérés en priorité.
- **Charge humaine** : la modération est le vrai coût. Prévoir **au moins deux modérateurs** formés avant d'ouvrir C2.

## 6. Priorité et enchaînement

1. **C1 après S4** (la charte et la relecture existent déjà) : commentaires modérés + comptes + réactions. Taille M.
2. **C2 après S7 et P2** : le forum a besoin d'audience (distribution, Baromètre) et de modérateurs. Taille L.
3. **C3** : seulement si C2 prospère.

Critères de réussite C1 : un commentaire invité et un commentaire de compte passent par la modération ; un spam est bloqué ; un commentaire signalé disparaît pour examen ; un utilisateur supprime son compte. C2 : section créée, sujet lié à un article, modération par section, aucun accès aux sujets verrouillés.

## 7. Pourquoi pas de blog par utilisateur (pour l'instant)

Un blog par personne multiplie la modération, les pages à indexer et les risques de diffamation, sans valeur journalistique garantie. Alternative déjà au plan : le **contributeur** (S4) publie une **Tribune** avec fiche auteur, après relecture. Si la demande existe, un **profil public** avec liste des contributions et messages du forum comblera 80 % du besoin ; le blog complet viendra seulement après C2.

## 8. Questions ouvertes

1. Commentaires **sans modération préalable** pour les comptes de confiance : acceptable à partir de quand ?
2. Qui modère au démarrage (vous, deux personnes) ?
3. Langues du forum : français d'abord, sections en pulaar/maninka/soussou/wolof quand des locuteurs modérateurs existent ?
4. Faut-il autoriser l'anonymat total pour les invités, ou exiger au minimum un e-mail vérifié ?

## Sources

- Nairaland : Wikipédia (fondation, fonction) ; St. Augustine explore (structure, modération) ; ThisDay, « A Case Study on Nairaland » (modèle publicitaire) ; TechCabal (coupure par Cloudflare, critique de la modération).
- Forums : django-machina (GitHub) ; Discourse (exigences matérielles : Docker, PostgreSQL, Redis, 1 Go de RAM minimum selon un guide tiers) ; comparatif Discourse/Flarum.
- Droit : DLA Piper Data Protection (Guinée) ; loi L/2016/037/AN (Cour suprême de Guinée, texte) ; Guinéenews (structure de la loi) ; allAfrica (HAC et cybersécurité, 26 juillet 2025).
