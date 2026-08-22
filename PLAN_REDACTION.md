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

| Phase | Contenu | Taille approx. |
| --- | --- | --- |
| **1** | Types de contenu, sources structurées, commentaires éditoriaux, historique de modifications | 3-4 jours |
| **2** | Rôle rédacteur, workflow à boucle (soumis/à relire/correction), file de relecture | 3-4 jours |
| **3** | Assistant IA (après décision sur l'API à utiliser) | 4-6 jours |
| **4** | Médiathèque réutilisable | 2-3 jours |
| Hors périmètre (§C) | Mode hors ligne, calendrier, notifications, analytique | Non chiffré — à revisiter une fois une vraie équipe en place |

## J. Prochaine étape

Je propose de commencer par la **Phase 1** — elle ne touche à aucune
permission ni au workflow de publication (donc aucun risque sur ce qui
tourne déjà en production), et donne une vraie valeur immédiate : types de
contenu, sources citables, commentaires internes, historique.

Dis-moi si je commence, ou si tu veux réordonner les phases.
