# Plan — Dictionnaire monolingue Pulaar (logique d'abord)

> Rédigé le 2026-11-22 à la demande du propriétaire. Références fournies par lui : `dictionnaire-pulaar-erd.mermaid` (schéma v5, 9 tables) et `v6_proposition_delta.sql` (proposition v6 du 21/11/2026, 21 tables, **non appliquée**).
> Principe fixé par le propriétaire : **la logique et les règles d'abord, les données ensuite.** Perdre les 22 termes actuels n'est pas un problème ; un modèle qui ne tient pas les bonnes règles en est un.

## 1. Cible (les décisions D1–D4 de la v6, reprises telles quelles)

- **D1** Le Pulaar est la base : une entrée n'est « validée » que si elle a une définition **en Pulaar**.
- **D2** Les autres langues sont des **mots de traduction**, jamais des définitions. Chaque traduction peut pointer vers un dictionnaire externe (Wiktionnaire / Wiktionary ou autre) par une adresse **construite à l'affichage** (`modèle avec {term}` + mot encodé). Aucune URL de mot stockée en dur.
- **D3** Sources premières multiples : la provenance est portée **par définition et par exemple** (source + localisation : page, n° d'entrée), pas seulement par terme. Chaque source a un **statut des droits** (par défaut « à vérifier »).
- **D4** Tout ce qui vient d'un fichier, d'un texte ou d'une IA entre par une **zone d'import**. L'IA propose, **un humain nommé valide**. Rien n'écrit directement dans le dictionnaire.

## 2. Évaluation de l'existant (app `pulaar`, 1 migration)

| Sujet | Aujourd'hui | Écart avec la cible |
|---|---|---|
| Entrée | `PulaarTerm` : lemme, classe grammaticale en texte libre, domaine, source unique, statut documenté/validé | Pas de dialecte, pas d'indice d'homonyme (deux mots écrits pareil fusionnent), pas de numéro de sens, classe grammaticale non contrôlée |
| Définition | `PulaarDefinition` : champ `lang` (ff/fr/en) | **Contredit D1/D2** : le français y est une définition. Pas de source ni de localisation par définition |
| Traductions | aucune table | à créer |
| Dictionnaires externes | aucun | à créer |
| Sources | `PulaarSource` : nom, lien, licence, méthode ; `PROTECT` | pas de statut de droits ; la licence est un texte libre |
| Import / IA | `PulaarProposal` (file de modération, une seule définition ff + fr) | pas de lot d'import, pas de texte brut conservé, pas d'auteur « IA / parseur / humain », pas de relecteur nominatif obligatoire |
| Règle « validé ⇒ définition Pulaar » | absente | à imposer |
| Morphologie | absente | racines, classes nominales, mutations consonantiques, extensions verbales, voix : à modéliser, **à remplir par un linguiste** |
| Relations / variantes | absentes | synonymes, dérivés, variantes dialectales |
| Exemples | absents | à créer, avec source |

Ce qui dépend de l'ancien modèle et sera touché : `mot_du_jour` (accueil), `sitemaps.py`, vues et gabarits `/pulaar/`, `wagtail_hooks.py`, `forms.py` (proposer un mot), `seed_pulaar` + `data/wiktionary.json`, les tests `pulaar/tests.py` et ceux de l'accueil.

## 3. Standards à suivre (ne rien inventer)

| Besoin | Standard | Usage prévu |
|---|---|---|
| Échange avec Webonary / FLEx (SIL) | **LIFT** (Lexicon Interchange FormaT, XML) | **Import** de dictionnaires publiés par leurs auteurs → zone d'import ; export LIFT |
| Publication / archivage scientifique | **TEI Lex-0** (sous-ensemble de TEI Dictionaries) | export optionnel, plus tard |
| Modèle conceptuel de l'entrée | **LMF (ISO 24613)** / **OntoLex-Lemon** (W3C) | inspiration : entrée lexicale → formes → sens ; pas d'implémentation RDF |
| Codes de langue et dialecte | **ISO 639-3** (`fuf` Pular de Guinée, `fra`, `eng`, `wol`…), étiquettes **BCP 47** pour l'affichage (`ff`, `fr`) | tables `Dialect`, traductions |
| Texte | Unicode **NFC** ; vraies lettres ɓ ɗ ŋ ƴ ; recherche tolérante (`ɗ→d`) déjà en place | normalisation à l'enregistrement |

À vérifier avec le propriétaire avant de coder : la liste exacte des étiquettes de dialecte (la v6 utilise `fuf-GN`) ; les codes sont ceux de l'ISO, le suffixe pays est une convention du projet.

Réserve : je n'ai pas relu les spécifications officielles dans cette session ; elles seront relues et citées dans le code avant l'import LIFT.

## 4. Modèle cible (Django, en s'appuyant sur la v6 — pas de SQL brut sur Supabase)

Le SQL v6 suppose des tables `lemmas`, `definitions`… Appliqué tel quel sur la base du site, il casserait les migrations Django. On **porte les règles** en modèles Django.

1. `Dialect` (code, nom, pays) — une ligne par variété ; aucune valeur inventée.
2. `PartOfSpeech` (code, nom français, nom Pulaar, verbal oui/non) — table, pas du texte libre.
3. `Entry` (ex-`PulaarTerm`) : `lemma`, `dialect`, `pos`, `homonym_index`, domaine, `status` (brouillon → documenté → validé), unicité `(dialect, lemma, pos, homonym_index)`.
4. `Sense` (ex-`PulaarDefinition`) : `entry`, `sense_number`, texte **Pulaar uniquement**, `source`, `source_locator`.
5. `Example` : rattaché à un sens, texte Pulaar + traduction facultative, source + localisation.
6. `Translation` : `entry` (et sens facultatif), langue ISO 639-3, mot, `external_dictionary` facultatif, source, `is_validated`. Unicité `(entry, langue, mot)`.
7. `ExternalDictionary` : code, nom, langue, `url_template` contenant `{term}`. **Liste blanche de domaines `https`** ; lien rendu avec le mot encodé, `rel="noopener nofollow"`.
8. `Source` : + `rights_status` (domaine public / autorisation accordée / en attente / à vérifier / restreint) + note. **Une source non « publiable » n'alimente pas l'affichage public.**
9. Import : `ImportBatch` (source, fichier, empreinte SHA-256, version du parseur, importé par) et `StagingEntry` (texte brut intact, JSON analysé, `proposed_by` = `parser:` / `ai:<modèle>` / `human:<nom>`, statut en attente / accepté / rejeté / fusionné, relecteur et date obligatoires dès que le statut change, note obligatoire si rejet). Remplace `PulaarProposal` (la page « proposer un mot » alimente cette file).
10. Plus tard (phase 5, structure seulement) : `Root`, `NounClass`, `VerbalExtension`, `MutationRule`, `EntryRelation`, `DialectalVariant`.

Règles imposées (en code + tests, car SQLite en test ne sait pas faire de déclencheurs) :
- une entrée ne passe à « validée » que si elle a au moins un sens en Pulaar ;
- on ne supprime pas le dernier sens d'une entrée validée ;
- un sens, un exemple ou une traduction sans source est refusé à l'enregistrement par un import ;
- une proposition « IA » ne peut être acceptée sans relecteur humain nominatif ;
- commande `verifier_dictionnaire` : liste les violations (entrées validées sans sens, sources sans droits clairs utilisées en public…). Lancée aux tests et en production.

## 5. Phases (une à la fois, comme pour le reste du backlog)

| Phase | Contenu | Besoin du propriétaire |
|---|---|---|
| **P0 — Cadrage** | Valider ce plan, la liste des dialectes, la liste des classes grammaticales, le rôle « relecteur » (qui valide ?), la politique de droits | **ses réponses (§6)** |
| **P1 — Noyau** | `Dialect`, `PartOfSpeech`, `Entry`, `Sense`, `Example`, `Source` + droits ; migrations propres (l'ancien modèle est remplacé, les 22 termes sont re-semés avec leur source) ; admin Wagtail ; adaptation de `/pulaar/`, accueil, sitemap, mot du jour (qui ne propose que des entrées **avec définition Pulaar**) ; tests | — |
| **P2 — Traductions** | `Translation` + `ExternalDictionary` + affichage des liens ; Wiktionnaire fr/en comme premiers dictionnaires externes | choix des dictionnaires externes |
| **P3 — Zone d'import** | `ImportBatch` / `StagingEntry`, écran de relecture dans Wagtail (accepter / fusionner / rejeter avec note), la page « proposer un mot » branchée dessus, `verifier_dictionnaire` | — |
| **P4 — Interchange** | Import **LIFT** (vers la zone d'import), export LIFT/CSV, API JSON en lecture seule | accord du propriétaire d'un dictionnaire avant tout import (Webonary : on prend un export que l'auteur publie, on ne moissonne pas) |
| **P5 — Morphologie** | Structure des racines, classes nominales, mutations, extensions verbales, relations, variantes | un **linguiste** : le modèle est prêt, le contenu vient de lui |
| **P6 — Interface de travail** | File « mots à définir en Pulaar » (entrées sans sens), tableau de bord de couverture (entrées / définies / validées / traduites), recherche par dialecte | — |

Chaque phase : modèle → tests → déploiement → vérification en production → mise à jour du HANDOFF.

## 6. Décisions attendues du propriétaire (P0)

1. **Dialectes** : quelles variétés au lancement ? (Fuuta Jaloo seul, ou aussi Fuuta Tooro, etc.) et les codes à utiliser.
2. **Classes grammaticales** : liste de départ en Pulaar et en français (je ne la remplis pas de mémoire).
3. **Qui valide ?** Rôle « Lexicographes Pulaar » existant : est-ce le seul groupe habilité à passer une entrée en « validée » ?
4. **Droits** : par défaut « à vérifier » = rien d'affiché publiquement tant que la source n'est pas passée à « autorisation accordée » ou « domaine public » ? (recommandé : oui)
5. **Dictionnaires externes** de départ pour les traductions (recommandé : Wiktionnaire fr, Wiktionary en) et langues de traduction à proposer.
6. **Source de référence** : quel dictionnaire sur Webonary exactement (nom ou lien) et son auteur, pour demander l'autorisation de réutilisation avant tout import.
7. **Reprise de l'existant** : confirmation qu'on repart propre (les 22 termes actuels sont re-semés avec leur source Wiktionnaire, rien de plus).

### Réponses du propriétaire (2026-11-22) — décisions prises

1. **Dialectes** : tous, Fuuta Jaloo (`fuf`) en premier, puis les autres dont Fuuta Tooro (`fuc`). Vision « dictionnaire universel » : macro-code `ful` + sous-code ISO 639-3 par entrée.
2. **Classes nominales** : une vingtaine (~24–26), à remplir depuis une source citée, jamais de mémoire.
3. **Validation** : le propriétaire valide en tant que lexicographe ; règles légères (seule règle dure : pas de « validé » sans définition en pulaar).
4. **Droits** : « à vérifier » par défaut ; rien de public tant que la source n'est pas autorisée.
5. **Dictionnaires externes** : Wiktionnaire fr, Wiktionary en.
6. **Source de référence** : Webonary https://www.webonary.org/pular/en/ (le site bloque les robots ; le propriétaire dispose d'une copie locale).
7. **Reprise** : les 22 anciens termes peuvent être abandonnés.

### État d'avancement (2026-11-22)

- **P1 (modèle) et P2 (vues, recherche, liens externes) : faits et en production.**
- **Import Abuu Sih** (« Saggitorde Mawnde », don de l'auteur) : page d'admin « Importer un lot (dictionnaire) », nettoyage déterministe du mot vedette (version `v6-nettoyage-1`), 10 lots ≈ 16 100 entrées, statut « documentée », source en droits « à vérifier » (forcé côté serveur), invisible au public, aperçu réservé à l'équipe, retrait d'un lot en un clic. Les données ne sont jamais dans le dépôt public.
- **Bloquant avant ouverture publique** : autorisation écrite d'Abuu Sih (remise orale seulement).
- À confirmer : dialecte `fuc` (hypothèse), classes grammaticales (déduites par Gemini).

### Contrôle qualité de l'import Abuu Sih (2026-11-22, en production, mis en attente par le propriétaire)

16 099 entrées, 17 361 sens, 1 159 variantes, 265 exemples. Cas douteux restants (non corrigés, à reprendre plus tard avec un lexicographe) :
- 48 mots vedettes contenant un espace : variantes collées (« Caakgol caakagol », « Hinnee Hinney ») ou vraies expressions (« Fendere weɗere ») — indécidable sans lecture humaine ;
- 24 mots avec majuscule interne ; défauts d'extraction isolés (« Copoƴƴ i », « turulle (ɗee) », « Boro - boro ») ;
- 91 définitions commençant par « ( » ; 13 définitions de moins de 8 caractères ;
- 810 entrées en classe « à préciser » ; 7 564 sans classe nominale (normal) ;
- les entrées d'une ou deux lettres (ƴ, Nj, Ng, Mb, Aa…) sont les lettres de l'alphabet : légitimes.
Reprise possible : sortir ces listes pour relecture, ajuster `importer.py` (version du parseur), retirer le lot et le réimporter.

## 6 bis. Liens automatiques dans les définitions (faisabilité mesurée le 2026-11-26)

**Demande** : transformer chaque mot d'une définition qui est lui-même une entrée en lien cliquable (lemmatisation, flexions, alternances de consonnes initiales, homonymes, mots-outils, résultat pré-calculé).

**Mesures sur les 17 361 définitions en production** (lecture seule, SQL) :

| Mesure | Résultat |
|---|---|
| Mots dans les définitions | 115 114 occurrences, 19 892 formes distinctes |
| Correspondance exacte avec un lemme ou une variante (autre entrée) | **63 %** des occurrences (59 154 avec ≥ 3 lettres) |
| … dont 15 mots seulement (*ina, ko, e, huunde, noon, mum, no, neɗɗo, goɗɗo, mbaydi…*) | 16 600 liens : du bruit, pas de l'aide |
| Après retrait des mots présents plus de 500 fois (25 mots) | 38 357 liens, **91 % des définitions** ont au moins un lien |
| Occurrences sans correspondance exacte | 35 % (14 343 formes distinctes) : surtout des formes conjuguées ou fléchies (*waɗa, tawi, wayi, njamɗe…*) |
| Retrouvées en ignorant ɓ ɗ ŋ ƴ (*ƴettude* → *Yettude*) | 912 occurrences seulement (1,5 %), avec risque de faux liens (*ɓe* ≠ *be*) |
| Retrouvées par alternance d'initiale (g/w, h/k, w/b… testées comme hypothèses) | de 2 à 666 occurrences par paire, **mais la plupart sont des faux rapprochements** (*waɗa* → *gaɗa*) |

**Ce qui est livré (fiable)** : tokenisation Unicode qui conserve ponctuation, espaces, lettres spéciales, Adlam ; correspondance **exacte** (casse ignorée) sur lemmes et formes variantes ; homonymes (lien principal = même variété puis plus petit n° d'homonyme, les autres dans `data-alternatives`, liste au survol/clavier) ; jamais d'auto-lien ; un lien par cible et par définition ; mots-outils : exclusion **automatique par fréquence** (statistique, aucun jugement de grammaire) + liste modifiable par l'équipe (« ne pas lier » / « toujours lier ») ; résultat stocké dans `PulaarSense.text_html`, recalculé par signaux (nouveau mot, mot supprimé, variante, définition modifiée, changement de droits d'une source) ; commande `hypertextualiser` (rattrapage, `--tout`, `--simuler`) exécutée à chaque déploiement.

**Règle de visibilité (essentielle)** : une définition d'une entrée *publique* ne pointe que vers des entrées *publiques* ; sinon le public verrait des liens vers des pages en 404 et la liste des mots non publics. Un changement de droits d'une source recalcule tout.

**Ce qui n'est PAS livré, et pourquoi** :
- **Lemmatisation des flexions** (pluriels, conjugaisons, extensions verbales) : elle demande des paradigmes validés (classes nominales, conjugaisons, suffixes) qui n'existent pas dans la base ; les deviner créerait des liens faux sans qu'on s'en aperçoive. Les entrées verbales sont à l'infinitif (*waɗde*), les définitions emploient des formes conjuguées (*waɗa*).
- **Alternances de consonnes** : le mécanisme existe (table « Alternances de consonnes », paires désactivées, jamais pré-remplies) mais, sans la classe nominale du mot, une alternance seule donne trop de faux rapprochements. À activer paire par paire, après `hypertextualiser --rapport --paires g:w` et validation par un lexicographe.
- **Rapprochement sans lettres spéciales** : prévu (`LIENS_APPROX`), désactivé par défaut.
- **Expressions à plusieurs mots** (48 entrées) : non liables mot à mot.
- Les exemples et les traductions ne sont pas hypertextualisés (extension possible).

**Pour monter en précision plus tard** : (1) remplir la classe nominale des noms, (2) fournir à la base les paires singulier/pluriel (relations « pluriel » / « singulier » déjà prévues), (3) valider un tableau de suffixes verbaux avec la source citée. Chaque règle validée alimente le palier suivant sans toucher au reste.

## 7. Risques

- **Perdre le fil entre « dictionnaire » et « base de données de recherche »** : le modèle accepte une structure riche (racines, mutations), mais **rien n'est affiché ni rempli sans linguiste**. Une structure vide vaut mieux qu'une donnée approximative.
- **IA ≠ autorité linguistique** : les propositions IA restent dans la zone d'import et portent la mention de leur origine jusqu'à la validation.
- **Droits** : un dictionnaire publié en ligne n'est pas pour autant libre de droits (cas du Dictionnaire Pular d'Oumar Bah sur Webonary : consentement requis).
- **Ordre d'écriture** (piège repéré dans la v6) : un déclencheur interdisant d'insérer une entrée déjà validée oblige à créer l'entrée non validée, puis son sens, puis à la valider. Les imports suivront cet ordre.
- **Lien externe** : toujours construit par l'application avec le mot encodé, jamais copié d'une saisie libre ; domaines en liste blanche.
