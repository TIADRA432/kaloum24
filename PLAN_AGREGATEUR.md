# Plan d'intégration — Agrégateur d'actualités autonome pour Kaloum24

> **État d'avancement : les 6 phases du MVP (Phase 0 à Phase 6) sont livrées,
> testées et vérifiées contre de vraies sources en production réelle** —
> voir le README, §5, pour le détail de ce qui tourne. Ce document reste tel
> qu'il a été écrit au départ, comme référence de conception et pour le
> détail des choix (notamment §0, sur la limite légale qui a orienté tout le
> reste). La section 3 (hors MVP) reste, elle, un vrai backlog : rien de ce
> qui y est listé n'a été construit.

Ce document traduit le cahier des charges en jours de travail effectif,
dans l'ordre où je recommande de les faire. « Jour » veut dire journée de
travail concentré sur ce chantier — pas jour calendaire. Si tu avances à
mi-temps entre tes autres projets, multiplie par deux le calendrier réel.

**Estimation totale : 18 jours de travail effectif** pour un MVP complet et
testé (sources, collecte, déduplication, scoring, modération, supervision).
Ce n'est pas gonflé — c'est ce que prend, fait sérieusement, un système qui
touche à huit sous-systèmes différents. Le détail jour par jour justifie ce
chiffre plus bas.

---

## 0. Le point qui conditionne tout l'ordre du plan

Ton cahier des charges distingue déjà trois modes (agrégation / importation
autorisée / synthèse) — c'est la bonne architecture. Mais il y a une
différence de nature entre ces trois modes qui doit déterminer **l'ordre
d'implémentation**, pas juste leur description :

- **Mode 1 (agrégation : titre + extrait + lien)** est une pratique
  standard et défendable — c'est ainsi que fonctionnent Google News ou
  Feedly. Un flux RSS publié par un site est une invitation implicite à la
  syndication de son contenu sous cette forme. C'est du **travail
  d'ingénieur pur** : je peux le construire de bout en bout.

- **Mode 2 (importation autorisée)** n'est pas une fonctionnalité qu'on
  développe — c'est un **accord commercial** qu'il faut d'abord obtenir de
  chaque source, un par un, avant que la moindre ligne de code n'ait de sens.
  Le code sera trivial une fois l'accord signé (un champ `licence_accordee`
  sur la source). Le vrai travail est en dehors de l'IDE.

- **Mode 3 (synthèse par IA)** ajoute un risque éditorial et un coût
  d'API récurrent (appels à un modèle de langage), et demande une
  supervision humaine stricte — une synthèse trop proche d'une seule source
  reste une reproduction déguisée, pas une création originale.

**Conséquence pratique : ce plan construit uniquement le Mode 1 comme MVP.**
Le Mode 2 devient une simple case à cocher sur une source une fois qu'un
accord existe. Le Mode 3 est noté en fin de document comme extension future,
avec ses coûts et risques propres, à ne construire qu'une fois le Mode 1 en
usage réel.

> **Je ne suis pas juriste**, et ce qui précède est une lecture générale, pas
> un avis juridique sur ta situation précise. Pour du Mode 2 en particulier —
> un vrai accord de republication — fais confirmer les termes par quelqu'un
> de qualifié avant de t'engager avec une source.

**Second point de vigilance, stratégique celui-là :** si les sources que tu
comptes agréger sont des concurrents directs de Kaloum24 (d'autres sites
d'actu guinéens), afficher leurs titres en bonne place sur ta page d'accueil
détourne du trafic vers eux — ce n'est pas neutre commercialement, même en
Mode 1. Vaut mieux le faire consciemment : soit tu choisis des sources
complémentaires plutôt que concurrentes (agences de presse internationales,
sources institutionnelles, thématiques que Kaloum24 ne couvre pas), soit tu
assumes que l'agrégateur sert d'abord le lecteur, quitte à envoyer du trafic
ailleurs.

---

## 1. Vue d'ensemble

| Phase | Jours | Livrable vérifiable | Statut |
| --- | --- | --- | --- |
| 0. Cadrage | J1 | Liste de sources retenue, robots.txt/CGU vérifiés, config MVP figée | ✅ Fait |
| 1. Fondations données | J2–J4 | Modèles + migration + CRUD sources dans l'admin | ✅ Fait |
| 2. Moteur de collecte | J5–J8 | `flask collect-sources` ramène de vrais articles en base | ✅ Fait |
| 3. Détection de doublons | J9–J10 | Deux articles du même événement se regroupent sous un même sujet | ✅ Fait |
| 4. Scoring configurable | J11–J12 | Chaque article collecté a un score et un badge, pondérations réglables | ✅ Fait |
| 5. File de modération | J13–J15 | Un admin accepte/rejette/édite, l'acceptation crée un vrai article Kaloum24 | ✅ Fait |
| 6. Attribution + supervision | J16–J17 | Attribution visible côté public, tableau de bord de surveillance | ✅ Fait |
| 7. Tests + durcissement | J18 | Suite de tests complète, gestion des pannes de flux | ✅ Fait en continu — chaque phase a été testée et vérifiée en conditions réelles à mesure, plutôt qu'en étape finale séparée (247 tests au total) |

---

## 2. Détail jour par jour

### Phase 0 — Cadrage (J1)

- Dresser la liste des sources candidates avec, pour chacune : a-t-elle un
  flux RSS/Atom ? Son `robots.txt` autorise-t-il la lecture automatisée ?
  Ses CGU mentionnent-elles la syndication ?
- Trancher : sources concurrentes ou complémentaires (voir §0).
- Figer le périmètre MVP : Mode 1 uniquement, dédoublonnage par
  similarité textuelle simple (pas de modèle sémantique au premier tour),
  validation humaine obligatoire avant publication (pas de publication
  automatique au départ, même si le score est élevé — on active
  l'automatisation seulement après avoir observé le système tourner en
  vrai).

**Livrable :** un tableau de 5 à 15 sources, chacune avec son URL de flux et
son statut de conformité (autorisée / à vérifier / écartée).

---

### Phase 1 — Fondations : sources et modèle de données (J2–J4)

**Esquisse du modèle** (à affiner en implémentation, pas figé ici) :

- **`Source`** — nom, URL du site, URL du flux RSS/Atom, type
  (rss/api/manuel), catégories surveillées, mots-clés inclus/exclus,
  fréquence de collecte, niveau de confiance (0–100), active ou non,
  conformité vérifiée (bool), notes CGU, dernière collecte, dernière erreur.
- **`CollectedArticle`** — la source, l'URL originale (unique par source,
  c'est la clé anti-doublon la plus simple), titre, extrait, image, auteur,
  date de publication, date de collecte, langue, statut (nouveau / groupé /
  noté / rejeté / publié), score total, détail du score, sujet associé.
- **`Topic`** — regroupe plusieurs `CollectedArticle` qui parlent du même
  événement : titre représentatif, nombre de sources qui en parlent,
  première apparition.
- **`ScoringConfig`** — une ligne (ou un historique versionné) avec les
  pondérations de chaque critère et les seuils des badges 🔴🟠🟡⚪.

**Jour par jour :**
- **J2** — Modèles, migration Alembic, tests de création/contraintes.
- **J3** — CRUD complet des sources dans l'admin (réutilise le style déjà
  en place pour Rubriques et Correspondants : mêmes tableaux, mêmes pills
  de statut). Champ obligatoire « conformité vérifiée » — pas de case
  cochée, pas de collecte possible sur cette source.
- **J4** — Bouton « Tester cette source » : récupère les 3 derniers items du
  flux et les affiche sans les enregistrer, pour valider la configuration
  avant activation. Tests de bout en bout de tout ce qui précède.

---

### Phase 2 — Moteur de collecte (J5–J8)

- **J5** — Intégration de `feedparser` (bibliothèque mature pour RSS/Atom,
  gère les variantes de format). Fonction qui lit un flux et retourne une
  liste normalisée d'items.
- **J6** — Commande `flask collect-sources` : parcourt les sources actives
  et conformes, respecte la fréquence configurée par source, enregistre les
  nouveaux items en `CollectedArticle`, ignore les URL déjà connues. Suit le
  même modèle opérationnel que les sauvegardes déjà en place — une commande
  Flask lancée par cron, pas de file de tâches distribuée (Celery/Redis)
  disproportionnée pour ce volume.
- **J7** — Politesse envers les sources : identifiant clair dans le
  User-Agent, respect d'un `Crawl-delay` s'il est présent, délai entre deux
  requêtes vers le même site, timeout et nouvel essai en cas d'échec
  temporaire sans bloquer les autres sources.
- **J8** — Gestion des pannes : un flux indisponible enregistre l'erreur sur
  la source (`dernière_erreur`) sans faire échouer la collecte des autres
  sources. Tests avec des flux factices (dont un cassé exprès).

**Livrable vérifiable :** lancer `flask collect-sources` avec de vraies
sources RSS ramène de vrais articles en base, visibles dans l'admin.

---

### Phase 3 — Détection de doublons et regroupement (J9–J10)

- **J9** — Dédoublonnage niveau 1 : URL identique (trivial, déjà couvert en
  Phase 2) et détection de similarité de titre avec `rapidfuzz`
  (bibliothèque légère, pas de dépendance lourde de machine learning). Seuil
  de similarité configurable.
- **J10** — Regroupement en `Topic` : quand deux articles dépassent le
  seuil, ils rejoignent le même sujet ; le compteur « nombre de sources »
  s'incrémente. Tests avec les trois exemples de titres donnés dans le
  cahier des charges.

**Limite assumée et documentée :** la similarité textuelle simple rate les
reformulations très différentes du même événement (les trois exemples du
cahier des charges sont assez proches lexicalement pour qu'elle fonctionne ;
un titre totalement différent sur le même sujet lui échapperait). Le
passage à une similarité sémantique (embeddings) est noté en backlog — ne
vaut le coût d'ingénierie et de dépendance qu'une fois observé, en usage
réel, que le regroupement simple laisse passer trop de doublons.

---

### Phase 4 — Moteur de scoring configurable (J11–J12)

- **J11** — Calcul du score à la collecte : importance (mots-clés/catégories
  pondérés), fraîcheur (fonction décroissante depuis la publication),
  popularité (nombre de sources dans le même `Topic`), pertinence
  thématique (correspondance mots-clés), fiabilité de la source (son
  niveau de confiance configuré). Somme pondérée selon `ScoringConfig`.
  Badge 🔴🟠🟡⚪ dérivé de seuils configurables.
- **J12** — Écran admin pour ajuster les pondérations et voir l'effet en
  direct sur un échantillon d'articles déjà collectés (avant de valider,
  pas seulement en aveugle). Tests : deux jeux de pondérations différents
  doivent produire des classements différents sur le même jeu d'articles.

---

### Phase 5 — File de modération éditoriale (J13–J15)

C'est la phase la plus proche de ce qui existe déjà (modération des
commentaires, création d'articles) — donc la plus rapide relativement à sa
taille.

- **J13** — Écran de file : liste des `CollectedArticle` par score
  décroissant, avec badge, source, sujet associé, actions Accepter /
  Rejeter / Archiver.
- **J14** — « Accepter » crée un vrai brouillon `Article` Kaloum24 (réutilise
  le pipeline existant : rubrique, résumé, contenu) pré-rempli avec le
  titre, l'extrait et le lien source — jamais publié automatiquement, comme
  tout autre article. L'admin peut éditer avant de publier, exactement
  comme pour un article WhatsApp.
- **J15** — Filtre par sujet (voir tous les articles regroupés sous un même
  `Topic` d'un coup, comparer les sources). Tests de bout en bout du cycle
  complet collecte → score → acceptation → brouillon → publication.

---

### Phase 6 — Attribution et supervision (J16–J17)

- **J16** — Attribution visible côté public sur les cartes d'articles
  agrégés : nom de la source, lien vers l'article original, mention claire
  qu'il s'agit d'un contenu agrégé et non d'un article Kaloum24 (distinction
  visuelle avec les articles rédigés en interne ou par WhatsApp — cohérence
  avec les badges déjà en place pour « Abonnés » et « Une »).
- **J17** — Tableau de bord de supervision, sur le modèle du tableau de bord
  existant : sources actives, articles collectés (24 h / 7 j), articles
  filtrés, articles publiés, sources en erreur, dernière synchronisation par
  source.

---

### Phase 7 — Tests de bout en bout et durcissement (J18)

- Suite de tests complète sur l'ensemble du sous-système (collecte, dédup,
  scoring, modération, attribution), avec des flux RSS factices — pas
  d'appel réseau réel dans les tests automatisés, sur le même principe que
  les tests WhatsApp qui simulent l'API Meta plutôt que d'y appeler
  vraiment.
- Limitation de débit sur la commande de collecte si elle est un jour
  exposée via une route web plutôt qu'une commande CLI.
- Vérification que `flask check-prod` couvre aussi ce sous-système (sources
  actives sans vérification de conformité, par exemple).

---

---

## 2 bis. Extension livrée hors plan initial — mode intégral gouvernemental/institutionnel

Non prévue dans le découpage J1–J18 ci-dessus : ajoutée après coup, à la
demande explicite d'un recentrage sur les sources gouvernementales et
institutionnelles, qui disposent souvent d'une autorisation de fait
(communiqués destinés à une reprise large par la presse) distincte du cas
général des médias commerciaux couvert par le Mode 2 du tableau ci-dessous.

Ce n'est **pas** le Mode 2 général du cahier des charges — pas d'accord
bilatéral requis ici, puisque la nature même d'un communiqué officiel
gouvernemental ou institutionnel implique généralement sa diffusion large.
Mais ce n'est pas non plus un blanc-seing : trois conditions cumulatives,
appliquées à la fois par le formulaire et par une contrainte en base
(`ck_source_integral_requires_justification`) :

1. la source est classée gouvernementale ou institutionnelle (jamais media) ;
2. une justification écrite d'au moins 20 caractères est enregistrée et
   conservée (accord, conditions publiées, ou communiqué qui se déclare
   lui-même libre de reproduction) ;
3. le flux fournit effectivement du contenu intégral pour l'item concerné —
   sinon repli automatique sur extrait + lien, sans erreur.

Vérifié contre un vrai flux institutionnel (fil de presse de l'OMS) : le
contenu intégral est correctement extrait, assaini deux fois (extraction
puis construction du brouillon), et une source reclassée « media » sur ce
même flux ne stocke jamais ce contenu, même s'il est techniquement présent
dans les items. La contrainte en base a été testée sur ses trois
contournements possibles, et la migration a été vérifiée pour ne pas casser
sur une base contenant déjà des sources (piège réel trouvé et corrigé : la
première version de la migration ajoutait les nouvelles colonnes en
`NOT NULL` sans valeur par défaut au niveau SQL).

Ce qui ne change jamais, y compris pour une source intégrale : tout reste
un brouillon, jamais publié sans relecture humaine.

---

## 3. Ce qui reste volontairement hors MVP

| Extension | Pourquoi elle attend | Taille approximative |
| --- | --- | --- |
| **Mode 2 — Importation autorisée (médias commerciaux)** | Nécessite un accord bilatéral par source avant tout code — distinct de l'extension gouvernementale/institutionnelle ci-dessus, qui elle est livrée | Quelques heures de code une fois l'accord obtenu |
| **Mode 3 — Synthèse par IA** | Coût d'API récurrent, risque éditorial (reproduction déguisée), supervision humaine renforcée à concevoir | 4–6 jours si retenu |
| **Dédoublonnage sémantique (embeddings)** | La similarité simple suffit tant qu'elle n'est pas prise en défaut en usage réel | 3–4 jours |
| **Popularité par engagement réel** (partages, clics) | Suppose d'abord un vrai volume de trafic à mesurer | 2 jours |
| **Publication automatique sans validation humaine** | À n'activer qu'après avoir observé la fiabilité du scoring sur plusieurs semaines — ne concerne aucune source, intégrale ou non | 1 jour (surtout de la confiance à construire, pas du code) |

---

## 4. Prochaine étape

Le MVP (Phase 0 à 6) est fait. Ce qui reste n'est plus une question de
jours de développement à planifier ici, mais de choix à faire à partir
d'un usage réel :

- **Observer d'abord.** Laisser tourner `flask collect-sources` par cron
  quelques semaines, avec les 12 sources vérifiées, et regarder ce qui
  arrive vraiment dans la file d'agrégation avant de construire quoi que ce
  soit de plus.
- **Puis choisir dans le backlog (§3)** en fonction de ce qu'on observe —
  par exemple, le dédoublonnage sémantique ne vaut le coût que si le
  regroupement par titres simple se révèle insuffisant en pratique, pas
  avant.

Dis-moi si tu veux qu'on attaque un point précis du backlog, ou qu'on
mette d'abord le site en production pour de vrai (voir README, §13).
