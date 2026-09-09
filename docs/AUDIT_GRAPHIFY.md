# Audit initial Kaloum24

Code de référence : `c2e94302a40f10637a7ce48ab8e9c577f57ac279`.
Méthode : graphe Graphify 0.9.56, extraction sémantique de 55 documents/gabarits/
visuels, parcours du graphe puis lecture des sources et sondes locales isolées.
Les modifications de cette livraison concernent uniquement l'outillage et la
documentation ; les défauts applicatifs ci-dessous restent à corriger.

## Constats prioritaires

| Priorité | Constat et preuve | Correction proposée |
| --- | --- | --- |
| P1 | **HTML non fiable dans l'aperçu RSS administrateur.** `feed_client.py:107` transmet le titre sans échappement ; `blueprints/admin.py:877` le retourne ; `templates/admin/sources.html:110` le concatène puis l'injecte avec `innerHTML` ligne 113. Une sonde Atom `type="text"` confirme que le titre `<img src=x onerror=alert(1)>` conserve ses balises jusqu'à cette insertion. Le script inline est autorisé par la CSP. | Créer les éléments DOM et assigner les titres avec `textContent`. Tester un flux hostile, en simulant le réseau. Exécution JavaScript réelle dans un navigateur non testée pendant cet audit. |
| P1 | **Configuration `.env` chargée après la classe Config.** `app.py:11` importe `Config`, dont les attributs lisent l'environnement immédiatement ; `load_dotenv()` n'arrive qu'à `app.py:22`. Une sonde remplaçant le chargeur par une valeur sentinelle confirme que `Config.SITE_NAME` conserve l'ancienne valeur. Impact sur `gunicorn app:app` ou l'import direct si les variables ne sont pas déjà exportées. Le CLI Flask peut masquer le problème en chargeant lui-même le fichier. | Charger `.env` avant l'import de Config ou lire l'environnement à la création de l'application. Tester import direct, Flask CLI et variables exportées. |
| P2 | **Exemption CSRF trop large pour les paiements.** `app.py:73` exempte tout `payments_bp`, donc aussi `/abonnement/checkout`. Une sonde avec utilisateur connecté, CSRF activé et Stripe simulé obtient 303 et un appel Stripe sans jeton. L'exploitation intersite dépend notamment des cookies SameSite ; il s'agit d'une protection absente, pas d'un débit financier démontré. | Exempter seulement `stripe_webhook`, conserver le jeton sur checkout et ajouter une régression 400 sans jeton / succès avec jeton. |
| P2 | **Publications Facebook bloquées par la CSP.** `templates/article.html:113` charge `connect.facebook.net`, mais `security.py:32` limite les scripts à l'origine locale et aux scripts inline. L'en-tête HTTP a été vérifié avec le client Flask. | Définir une autorisation ciblée sur les pages concernées, ou proposer un lien externe explicite. Vérifier aussi les frames nécessaires dans un navigateur. |
| P2 | **Newsletter sans enregistrement.** `templates/base.html:161` annule la soumission et change seulement le texte du bouton en « Inscrit ». Aucun endpoint ni stockage ne participe à ce formulaire. | Implémenter inscription persistante et retour d'erreur, ou retirer la promesse d'inscription jusqu'à disponibilité. |
| P2 | **Suite de tests non portable sous Windows.** L'exécution initiale atteint 111 assertions PASS, aucune FAIL, puis s'arrête à `tests_fonctionnels.py:644` : suppression d'un fichier SQLite encore ouvert (`WinError 32`). Le reste de la suite n'a donc pas été exécuté localement. | Retirer les sessions, disposer les moteurs avant suppression et utiliser une isolation par fixture. Le workflow lance aussi la suite existante sur Linux pour distinguer défaut de portabilité et régressions métier. |

## Architecture et améliorations proposées

- **Découper progressivement l'administration** : `blueprints/admin.py` concentre
  rédaction, commentaires, agrégation et lexicographie. Extraire un domaine à la
  fois en conservant les endpoints et des tests sur les permissions.
- **Rendre les webhooks idempotents** : `_traiter_message` ignore l'identifiant
  Meta ; une livraison répétée peut ajouter deux fois le texte au brouillon.
  Stocker les identifiants traités, puis envisager une file de traitement avec
  accusé de réception rapide et reprise des erreurs. Prévoir aussi des tests de
  doublons et d'ordre des événements Stripe.
- **Réduire les requêtes globales** : `inject_globals` compte les commentaires en
  attente et la file d'agrégation pour tout rendu, y compris public. Réserver
  ces compteurs aux pages et rôles concernés, puis mesurer les requêtes par page.
- **Clarifier la maturité fonctionnelle** : distinguer dans le README ce qui est
  implémenté, décoratif et planifié ; vérifier ensemble newsletter, réseaux
  sociaux, statuts éditoriaux et rôles avant les prochaines fonctionnalités.
- **Renforcer les tests métier** : routes/permissions, paiements, import RSS,
  migrations sur base vide et existante ; isoler les API externes. La suite
  actuelle est un long script qui s'arrête à la première exception.

Ordre recommandé : P1 → corrections CSRF/Facebook/newsletter → fiabilisation des
tests et webhooks → découpage de l'administration → nouvelles fonctionnalités.
Le prochain prompt d'amélioration sera rapproché de cette liste avant toute
modification du comportement de l'application.

## Limites du graphe

Le graphe initial complet contient 677 nœuds, 1 304 arêtes et 69 communautés
après exclusion du JavaScript tiers. La CI génère séparément un graphe AST du
code courant, sans extraction sémantique automatique. Les fichiers d'outillage
ajoutés sont inclus dans le graphe ; les résultats ne décrivent pas un serveur
déployé et ses secrets ne sont pas consultés.

Deux gabarits de réinitialisation sont exclus par le filtre sensible de
Graphify, mais ont été lus séparément. Les références sans cible résolue et les
relations fusionnées sont documentées dans `diagnostics.json`. Les relations
sémantiques aident à naviguer mais ne prouvent pas une exécution. Les documents
peuvent décrire des intentions ; les constats ci-dessus sont vérifiés dans le code.

Les compteurs de jetons des sous-agents ne sont pas exposés par l'outil de
délégation ; leur coût réel n'est pas mesurable ici. Les zéros du rapport
automatique ne signifient pas une extraction sémantique gratuite.

Preuves locales : `graphify-out/audit-probes.log`, `tests-fonctionnels.log`,
`query-payments.txt`, `query-rss.txt`, `provenance.json` et `diagnostics.json`.
