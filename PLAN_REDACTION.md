# Plan — Kaloum24 vers une vraie salle de rédaction

> **Préalable qui conditionne tout le reste** : ce document ne repose pas sur
> Payload CMS. Kaloum24 est un projet Flask/Python avec base PostgreSQL,
> déployé et fonctionnel sur Render (`kaloum24.onrender.com`), 354 tests
> automatisés. Tout ce qui suit s'appuie sur cette architecture existante —
> voir README, §Structure du projet, pour l'état réel du code.

---

## A. Architecture actuelle (audit)

- **Modèles** : `Article` (avec statuts brouillon/en_relecture/programme/
  publie/archive, `scheduled_at`, `source`/`source_url` pour l'agrégateur et
  les réseaux sociaux), `Category`, `Comment` (lecteurs, imbriqués),
  `User` (rôles user/moderateur/admin), `ModerationLog`.
- **Éditeur** : Quill (gras, italique, titres H2/H3, listes, liens, image
  insérée dans le texte). Une seule image principale par article, avec
  crédit.
- **Workflow** : brouillon → (en_relecture) → (programme) → publié →
  (archive). Pas de boucle de correction, pas d'étape de soumission/relecture
  formalisée, pas de rôle intermédiaire entre rédacteur et admin.
- **Rôles** : 3 niveaux (user, moderateur, admin) — un moderateur peut déjà
  créer/modifier/publier n'importe quel article, aucune notion de rubrique
  assignée ni de permission par rubrique.
- **Traçabilité** : le `ModerationLog` capture les actions de modération
  (commentaires, bannissements) mais pas l'historique champ par champ d'un
  article (pas de "titre modifié à 09:30").
- **IA** : aucune intégration LLM dans le produit lui-même à ce stade.

## B. Ce qui manque vraiment, par ordre de valeur

1. **Types de contenu** (article, brève, dépêche, reportage, interview…) —
   change les champs pertinents sans complexifier le modèle central.
2. **Sources structurées** sur un article rédigé manuellement — aujourd'hui
   seuls les articles issus de l'agrégateur ont une source tracée.
3. **Commentaires éditoriaux internes** — distincts des commentaires
   lecteurs déjà en place, entre un relecteur et l'auteur.
4. **Historique des modifications** — qui a changé quoi, quand.
5. **Workflow à boucle** (soumis → à relire → correction demandée → validé)
   plutôt que la ligne droite actuelle.
6. **Rôle « chef de rubrique »** avec rubriques assignées.
7. **Assistant IA de rédaction** — correction, réécriture, titres, SEO.
8. **Médiathèque réutilisable** — aujourd'hui, une image = un upload = liée à
   un seul article, jamais réutilisée ni cherchée.

## C. Ce qui reste hors périmètre, sciemment

| Demandé | Pourquoi ça attend |
| --- | --- |
| Mode hors ligne + synchronisation | Refonte complète en SPA/PWA — des semaines à elle seule, sans lien avec le reste |
| Calendrier éditorial visuel | Utile une fois qu'il y a plusieurs rédacteurs actifs, pas avant |
| Notifications | Suppose d'abord des comptes rédacteurs réels à notifier |
| Analytique de performance par journaliste | Même raison — inutile tant qu'il n'y a qu'un compte admin |
| Contenu « Live »/événementiel | Fonctionnalité à part entière, aucun signal qu'elle est nécessaire maintenant |
| Recherche web intégrée pour journalistes | Récupérable plus tard via le même moteur IA que le reste |

## D. Rôles et permissions — proposition

Étendre les 3 rôles actuels à 4, en ajoutant *rédacteur* (le futur
« journaliste ») entre *user* et *moderateur* :

- **rédacteur** : crée et modifie ses propres articles, les soumet ; ne peut
  ni publier ni modifier les articles des autres.
- **moderateur** (renommé conceptuellement « chef de rubrique ») : relit,
  commente, valide, publie — pour l'instant sans restriction par rubrique
  (l'assignation rubrique-par-rubrique est en section C, hors périmètre
  immédiat, à ajouter si une vraie équipe se constitue).
- **admin** : inchangé, contrôle total.

## E. Workflow éditorial — proposition

```
brouillon → soumis → a_relire → (correction_demandee → brouillon)
                                 → valide → programme/publie → archive
```

Chaque transition est un simple changement de `status`, sur le modèle de ce
qui existe déjà pour brouillon/en_relecture/programme — pas une
réarchitecture, une extension.

## F. Collections/modèles nécessaires

- `Article` : ajouter `article_type`, `surtitre` (le titre existant fait
  déjà office de titre principal ; chapô = `summary`, déjà en place)
- `ArticleSource` (nouveau) : nom, url, type, citation — plusieurs par
  article
- `EditorialComment` (nouveau) : article, auteur, contenu, résolu (bool) —
  distinct de `Comment` (lecteurs)
- `ArticleRevision` (nouveau, léger) : article, champ modifié, ancienne
  valeur, nouvelle valeur, auteur, date

## G. Interface

- **Espace rédacteur** : liste de SES articles par statut, bouton
  « Soumettre à la relecture »
- **File de relecture** (pour moderateur/admin) : les articles `soumis`,
  avec les mêmes actions que la file d'agrégation déjà construite (page,
  filtres, actions) — réutilise le patron déjà en place, pas un nouveau
  design
- **Sur chaque article** : un fil de commentaires éditoriaux, sous le
  formulaire d'édition

## H. Architecture IA (si retenue en Phase 3)

Nécessite une vraie décision avant tout code : quelle API (Anthropic,
OpenAI, autre), quel budget, quelles limites d'usage. Rien de tout ça n'est
configuré aujourd'hui — à trancher explicitement, pas supposé.

## I. Plan de phases

| Phase | Contenu | Taille approx. | Statut |
| --- | --- | --- | --- |
| **1** | Types de contenu, sources structurées, commentaires éditoriaux, historique de modifications | 3-4 jours | ✅ Fait — 373 tests, vérifié en conditions réelles |
| **2** | Rôle rédacteur, workflow à boucle (soumis/à relire/correction), file de relecture | 3-4 jours | ✅ Fait — 398 tests, permissions vérifiées dans les deux sens |
| **3** | Assistant IA (après décision sur l'API à utiliser) | 4-6 jours | À faire |
| **4** | Médiathèque réutilisable | 2-3 jours | À faire |
| Hors périmètre (§C) | Mode hors ligne, calendrier, notifications, analytique | Non chiffré — à revisiter une fois une vraie équipe en place | — |

## J. Prochaine étape

Je propose de commencer par la **Phase 1** — elle ne touche à aucune
permission ni au workflow de publication (donc aucun risque sur ce qui
tourne déjà en production), et donne une vraie valeur immédiate : types de
contenu, sources citables, commentaires internes, historique.

Dis-moi si je commence, ou si tu veux réordonner les phases.

---

## K. Éditeur — Phase A (livrée)

Suite à la demande d'un éditeur de type Word/Notion pour Calum24 : plutôt
que de remplacer Quill par Lexical/Tiptap/ProseMirror (chacun un projet à
part entière), la Phase A étend l'éditeur existant. Vérifiée avec un vrai
navigateur (Playwright), pas seulement en théorie :

- **Nettoyage du collage Word/Google Docs** — les styles `mso-*`, classes
  `MsoNormal` et paragraphes vides disparaissent, le texte utile et sa mise
  en forme de base (gras, italique) sont conservés
- **Upload d'image par glisser-déposer et par collage (Ctrl+V)** — réutilise
  le point d'entrée déjà existant du bouton image de la barre d'outils
- **Compteur de mots et temps de lecture**, recalculé en direct
- **Mode plein écran** de rédaction

Un vrai trou de permission trouvé en cours de route : la route d'upload
d'image était encore réservée aux modérateurs depuis la Phase 2 — un
rédacteur ne pouvait pas insérer d'image dans son propre article. Corrigé.

Phases B (tableaux, citation avec attribution, embed YouTube) et C (blocs
éditoriaux ciblés) restent à faire, non commencées.

---

## L. Éditeur — Phase B (livrée en partie)

- **Embed YouTube** — extension prudente et testée du sanitizer central
  (`utils.sanitize_html`) : `<iframe>` reste interdit partout ailleurs,
  autorisé uniquement avec un `src` strictement validé par regex vers
  `youtube.com/embed/` ou `youtube-nocookie.com/embed/` — 12 cas d'attaque
  testés (domaine déguisé, `javascript:`, `data:`, phishing en https
  légitime, gestionnaires d'événements injectés, bypass de casse) en plus
  des cas légitimes, tous vérifiés automatiquement. Le rendu visuel du
  lecteur YouTube lui-même n'a pas pu être confirmé dans le navigateur
  headless de test malgré un accès réseau réel confirmé et un balisage
  strictement conforme au format officiel — même limite que le widget
  Facebook plus tôt dans ce projet, probablement propre à l'environnement
  de test, pas une anomalie du code.
- **Citation avec attribution** — un vrai bug trouvé et corrigé en cours de
  route : Quill reconstruit le HTML inséré à partir de son propre modèle
  interne et ne conserve que les formats qu'il connaît nativement, pas les
  classes CSS personnalisées. Corrigé en utilisant l'italique (format
  natif) plutôt qu'une classe qui disparaissait silencieusement.

**Tableaux : non commencés.** Nécessite un module tiers (Quill 1.3.7 n'a
pas de support natif satisfaisant), donc une vraie dépendance
supplémentaire à vendre et tester — reporté, pas fait à la légère.

---

## M. Éditeur — Phase B (complète)

**Tableaux — option 2 retenue.** Un vrai module tiers compatible Quill
1.3.7 existe (`quill1.3.7-table-module`, audité : code propre, licence MIT,
aucun appel réseau caché) mais n'est distribué qu'en module ES pur —
l'intégrer aurait exigé une carte d'import et un pont JS, avec un nouveau
risque qu'aucune autre fonctionnalité de ce projet n'a : si le module tiers
échoue à charger, l'éditeur entier pourrait ne plus s'initialiser.

Choix retenu à la place : un tableau est un **bloc atomique** dans Quill
(même principe que ses images ou vidéos), construit via un petit modal
séparé (une ligne de texte par ligne du tableau, cellules séparées par
« | »), inséré via un Blot Quill personnalisé (`blots/block/embed`) —
zéro dépendance tierce. Pas de fusion de cellules, pas de redimensionnement,
pas d'édition cellule par cellule dans l'éditeur — pour changer une valeur,
on retire le tableau et on en réinsère un.

**Une découverte empirique qui a motivé ce choix** : Quill 1.3.7 sans
module dédié aplatit silencieusement toute balise `<table>` insérée en
simples paragraphes, perdant toute la structure — vérifié directement
avant d'écrire le code, pas supposé.

**Un vrai bug CSS trouvé et corrigé en cours de route** : la règle
`.modal-overlay { display: flex }` avait une spécificité plus forte que
l'attribut HTML `hidden`, donc le modal restait visuellement affiché et
bloquait les clics même quand il aurait dû être caché.

Sanitizer étendu pour `table`/`thead`/`tbody`/`tr`/`th`/`td`, sans aucun
attribut autorisé — vérifié avec de vraies tentatives d'injection
(`colspan`, `style`, `onclick`, `<script>` dans une cellule), toutes
neutralisées sans casser la structure du tableau.

**Phase B est maintenant complète** : embed YouTube, citation avec
attribution, tableaux.

---

## N. Audit de robustesse (données)

Suite à une demande explicite de robustesse sur l'ensemble éditorial,
plutôt que d'ajouter une nouvelle fonctionnalité :

**Un vrai problème structurel trouvé et corrigé.** Aucune des clés
étrangères pointant vers `articles` (sources citées, commentaires
éditoriaux, historique des modifications, commentaires lecteurs, lien
`published_article_id` de l'agrégateur) n'avait de comportement `ondelete`
défini au niveau de la base de données — seule la discipline de l'ORM
(`cascade="all, delete-orphan"` côté SQLAlchemy) protégeait contre les
données orphelines, uniquement quand la suppression passe par l'ORM.

**Une découverte qui a surpris pendant l'audit** : SQLite, la base
utilisée pour tous les tests locaux depuis le début de ce projet, n'a
*jamais* appliqué les contraintes de clé étrangère par défaut (`PRAGMA
foreign_keys` est désactivé par connexion sauf activation explicite) —
contrairement à PostgreSQL, la vraie base de production, qui les applique
nativement. Autrement dit : cette protection n'a jamais été testée pour de
vrai localement jusqu'à cet audit, seulement supposée.

**Correctif** : `ondelete="CASCADE"` pour les sources citées, commentaires
éditoriaux, historique et commentaires lecteurs (n'ont pas de sens sans
leur article) ; `ondelete="SET NULL"` pour le lien de l'agrégateur
(`collected_articles.published_article_id`) — l'historique de collecte
doit survivre même si l'article publié est supprimé.

**Un piège de migration trouvé en le corrigeant** : aucune de ces
contraintes n'avait jamais reçu de nom explicite depuis la création du
projet — dropper une contrainte non nommée en mode batch Alembic échoue
avec "Constraint must have a name". Corrigé en découvrant le vrai nom à
l'exécution via l'inspecteur SQLAlchemy, plutôt que de supposer la
convention de nommage d'un moteur donné (elle diffère entre SQLite et
PostgreSQL). Testé dans les deux sens (upgrade et downgrade), et avec les
clés étrangères explicitement activées pour confirmer le comportement réel
de cascade — pas seulement que la migration s'applique sans erreur.
