# Plan — Module Pulaar dans Kaloum24 (Phase 1 / MVP)

> S'appuie directement sur `catalogue_ressources_pulaar.md` (recherche de
> faisabilité) et sur les 35 ressources cataloguées. Le document original
> (« Pulaar Ecosystem », 30 sections) décrit un programme pluriannuel — ce
> plan ne couvre que la Phase 1 recommandée par la recherche : un
> dictionnaire soigné, une recherche, une file de contribution modérée.
> Rien d'autre n'est engagé sans confirmation explicite.

---

## A. Ce qui change de posture par rapport au document original

- **Pas de Payload CMS, pas de microservice séparé** — un nouveau blueprint
  Flask (`blueprints/pulaar.py`) dans l'architecture Kaloum24 existante,
  même base Postgres, mêmes conventions.
- **Pas d'ingestion automatique de DiLAF ni de Webonary Burkina Faso** tant
  que l'autorisation n'est pas obtenue pour Kaloum24 spécifiquement — celle
  de DiLAF concernait l'accord entre Michigan State University Press et le
  projet DiLAF lui-même, pas un transfert automatique. Ces deux pistes
  restent les meilleures à contacter, mais rien n'est importé avant réponse.
- **Semence de départ = uniquement Wiktionary (« ff », CC BY-SA, avec
  attribution)** — le seul jeu de données dont la réutilisation est déjà
  claire aujourd'hui. Couverture reconnue comme faible : quelques dizaines
  à centaines d'entrées probables, pas des milliers. Le dictionnaire
  démarrera donc petit, pas rempli artificiellement.
- **Aucune fonctionnalité de proposition de terminologie scientifique
  « officielle »** en Phase 1 — seulement une suggestion de mot simple,
  modérée, jamais présentée comme validée. La question de partenariat
  institutionnel (CLAD, université guinéenne) reste posée, pas résolue.

---

## B. Identité visuelle — Tiadra Consortium, strictement localisée

Confirmé : la section `/pulaar` porte l'identité Tiadra Consortium
(Bordeaux Profond `#5D2E38`, Or Consortium `#D19F5E`, Roboto Slab +
Montserrat), **distincte** du reste de Kaloum24 (rouge/noir, style
journal) — un choix délibéré, pas une incohérence à corriger.

Mise en œuvre technique pour ne jamais laisser fuir cette identité sur le
reste du site :
- Nouvelle feuille de style `static/css/pulaar.css`, chargée uniquement
  sur les gabarits `/pulaar/*` (jamais sur `base.html` global).
- Variables CSS propres, préfixées (`--tc-bordeaux`, `--tc-or`, etc.) —
  jamais de réécriture des variables `--ink`/`--paper`/`--gold` du thème
  Kaloum24 existant.
- Logo, symbole et motif hexagonal auto-hébergés dans
  `static/img/tiadra/` (copiés depuis les assets de la skill).
- Roboto Slab et Montserrat auto-hébergées en `.woff2` dans
  `static/fonts/`, comme le reste du projet — jamais un lien Google Fonts
  en direct au moment du rendu.
- Boutons, cartes, séparateurs, iconographie : suivent le système
  graphique du guide (angles nets, accent hexagonal, boutons Or/Bordeaux)
  plutôt que de réutiliser les composants `.btn`/`.pill` déjà stylés pour
  l'identité rouge/noir de Kaloum24.

---

## C. Modèle de données (réduit du spec complet à 18 entités)

```
Term
  id, lemma (mot pulaar), part_of_speech, status
  (proposed / documented / validated — 3 états, pas 7)

Definition
  term_id, lang (fr/en), text

Domain
  name, slug  (ex. Technologie, Quotidien, Agriculture)

Source
  name, url, license, method (wiktionary / contribution / import_manuel)
  — jamais de donnée sans source rattachée, conforme au principe de
  provenance de la recherche précédente

Proposal
  term_lemma, definition_fr, domain_id, justification,
  proposed_by (user_id), status (en_attente/validé/rejeté)
  — la file de contribution modérée, sur le même principe que
  CollectedArticle/EditorialComment déjà construits ailleurs dans Kaloum24
```

Volontairement absents de la Phase 1 : Translation multi-langue au-delà
fr/en, Variant/Region, Example, Resource (bibliothèque), Corpus/
CorpusSentence, Audio, Contributor (réutilise `User` existant), Review
(fusionné dans Proposal.status), Revision (historique — pourrait réutiliser
le patron `ArticleRevision` déjà construit, si besoin réel démontré),
Tag. Ajoutables plus tard sans réécrire ce qui existe déjà.

---

## D. Routes

**Public**
- `GET /pulaar` — recherche centrale, page d'accueil du module
- `GET /pulaar/terme/<slug>` — fiche d'un terme (partageable)
- `GET /pulaar/domaine/<slug>` — termes d'un domaine
- `POST /pulaar/proposer` — formulaire de suggestion, va en file de
  modération, jamais publié directement

**Admin** (réutilise `moderator_required`, déjà en place)
- `/admin/pulaar` — tableau de bord (nombre de termes, propositions en
  attente)
- `/admin/pulaar/termes` — gestion des termes
- `/admin/pulaar/propositions` — file de modération

---

## E. Ce qui reste hors Phase 1, explicitement

| Reporté | Pourquoi |
| --- | --- |
| Audio/prononciation | Nécessite consentement de locuteurs, stockage, modération dédiée |
| Corpus aligné pulaar-français-anglais | Aucune source ouverte substantielle trouvée — à construire à partir du contenu bilingue de Kaloum24 lui-même, plus tard |
| Variantes régionales structurées | Multiplie le travail de modélisation ; à ajouter une fois le dictionnaire de base stable |
| API publique `/api/v1/pulaar` | Lecture seule envisageable tôt, mais pas avant que les données de base soient fiables |
| Terminologie scientifique « officielle » | Nécessite un partenariat institutionnel réel, pas encore engagé |
| Import/export CSV/JSON/TMX/RDF | Utile mais pas bloquant pour un MVP |

---

## F. Prochaine étape

Si ce découpage convient, je construis la Phase 1 dans cet ordre : modèle
de données + migration → routes publiques (recherche, fiche terme) →
habillage Tiadra Consortium → formulaire de proposition + file de
modération admin → seed Wiktionary (petit volume, honnête) → tests → vraie
vérification en local avec un navigateur → déploiement.

Dis-moi si je commence, ou si tu veux ajuster le découpage d'abord.

---

## G. Phase 1 — livrée

Modèle de données, blueprint public (`/pulaar`), routes admin complètes
(domaines, termes, file de modération des propositions), identité Tiadra
Consortium strictement confinée à `/pulaar` (feuille de style séparée,
polices auto-hébergées, jamais de fuite vers le reste du site).

**22 termes réels amorcés depuis Wiktionary** (`flask seed-pulaar`) —
extraits via l'API officielle (`Category:Fula lemmas`), formes de racine
exclues, traduits en français à la main, figés dans
`data_seed_pulaar_wiktionary.json` plutôt que dépendants d'un appel réseau
à chaque déploiement. Idempotent, vérifié.

Vérifié avec un vrai navigateur : recherche, fiche terme avec provenance
affichée, cycle complet inscription → proposition → modération → acceptation
→ visible publiquement.

**Deux vrais bugs trouvés et corrigés en cours de route** :
- `/pulaar` redirigeait vers `/pulaar/` (comportement Flask standard sur
  les routes de blueprint en `/`, mais une friction inutile pour une page
  d'entrée publique) — corrigé avec `strict_slashes=False`.
- Un test de non-retraitement d'une proposition déjà acceptée échouait
  à cause d'un jeton CSRF capturé sur une page dont le formulaire pertinent
  avait disparu (proposition déjà traitée, filtre par défaut) — même classe
  de piège que rencontrée plus tôt dans ce projet, corrigé avec une source
  de jeton fiable indépendante de l'état filtré de la page.

**483 tests automatisés au total**, vérifiés depuis une installation
vierge.

Prochaine étape naturelle si on continue : Phase 2 (audio, variantes
régionales, corpus) — non commencée, non planifiée en détail.

---

## H. Pulaar dans le module lui-même (interface + définitions)

**Définitions en pulaar** — le modèle acceptait déjà n'importe quelle
langue ; ajout du champ `ff` au formulaire admin et à l'affichage public
(pulaar affiché AVANT le français : c'est la langue du dictionnaire). La
recherche couvre automatiquement ce texte, sans filtre de langue. Reste
facultatif : personne n'est forcé d'inventer une définition pulaar pour
enregistrer un terme.

**Interface en pulaar** — règle absolue posée dans `pulaar_i18n.py` :
**aucune traduction inventée**. Je ne parle pas pulaar ; produire du
pulaar approximatif généré par IA sur un site dont le sujet EST le pulaar
serait précisément le problème de légitimité identifié dans la recherche.

Chaque terme provient de la **localisation fulah officielle de Firefox**
(`mozilla-l10n/firefox-l10n`, locale `ff`, MPL 2.0), réalisée par Ibrahima
Sarr, qui travaille avec la Commission Fulfulde (FULCOM) de l'ACALAN. La
provenance exacte (fichier + clé Mozilla) est notée pour chaque terme, donc
vérifiable par n'importe qui.

Termes attestés utilisés : Yiylo (chercher), Ɗemngal (langue), Suɓo
(choisir), Helmere (mot), Ɓeydu (ajouter), Neldu (envoyer), walla (ou).

Les chaînes sans équivalent attesté (« dictionnaire », « domaine »,
« proposer un mot »…) **restent en français**, et l'interface affiche
ouvertement le taux de couverture (7/15) à l'utilisateur plutôt que de
laisser croire à une traduction complète.

**À faire** : un locuteur pulaar doit relire et compléter les chaînes
manquantes — c'est du travail humain, pas quelque chose que je dois
fabriquer.
