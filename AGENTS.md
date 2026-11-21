# Kaloum24 — Guide pour agents et contributeurs (IA ou humains)

> Fichier d'entrée unique. Lis-le en entier, puis `docs/HANDOFF_AGENT.md`. **Aucun secret dans ce dépôt, ni dans Confluence, ni en conversation.**

## 1. Contexte en 30 secondes

Kaloum24 = portail d'actualités guinéen en français + dictionnaire Pulaar. La cible est la **V2 Wagtail/Django** (`v2/site/`, branche `feat/kaloum24-v2-render`, en production sur Render + Supabase). La V1 Flask (racine) est hors service : référence fonctionnelle seulement. Propriétaire/décideur : **Samba (Abdourahmane Barry)**, Conakry ; il valide par « go » / « continue ». Réponses en français, directes.

## 2. Où trouver quoi

| Besoin | Document |
|---|---|
| État du projet, pièges, reste à faire | `docs/HANDOFF_AGENT.md` |
| Technique (stack, apps, variables, build, tests) | `docs/ARCHITECTURE_TECHNIQUE.md` |
| Backlog priorisé, sprints S0–S8, décisions, risques | `docs/PLAN_EVOLUTION.md` (§5 bis, §6, §7) |
| Baromètre des prix (P1–P4) | `docs/PLAN_OBSERVATOIRE_PRIX.md` |
| Commentaires, comptes, forum (C1–C3) | `docs/PLAN_COMMUNAUTE.md` |
| Écrire/publier un article | `docs/GUIDE_REDACTION_WAGTAIL.md` |
| Référence de pilotage partagée | Confluence : page racine « Kaloum24 » (miroir de `docs/`) |

**Source de vérité : le dépôt (`docs/`).** Confluence et le Project Claude sont des miroirs de lecture ; en cas d'écart, le dépôt gagne, puis on resynchronise.

## 3. Rôles

| Rôle | Peut | Ne peut pas |
|---|---|---|
| Propriétaire (Samba) | décider, valider, saisir les secrets dans Render, publier | — |
| Agent de développement | coder, tester, committer sur sa branche, déployer via l'outil prévu, vérifier | choisir seul une décision listée en `PLAN_EVOLUTION` §6, toucher aux secrets |
| Agent éditorial | préparer des articles (`news/data/articles/*.json`, ou brouillon Wagtail) | publier du contenu inventé, valider du Pulaar |
| Relecteur (humain ou agent distinct) | vérifier l'agent qui a produit | relire son propre travail pour les chantiers à risque |
| Lexicographe Pulaar (humain) | seul à valider le Pulaar | — |

## 4. Règles non négociables

1. **Jamais de secret** (clé, mot de passe, `DATABASE_URL`, jeton) dans un fichier, un commit, une page Confluence, un message. Les non-secrets passent par MCP Render ; les secrets, c'est le propriétaire dans le tableau de bord.
2. **Aucun contenu inventé** : pas d'article, de chiffre, de prix, de traduction pulaar « approximative ». Chaque donnée a une provenance.
3. **IA ≠ autorité linguistique.** Pulaar généré par IA = jamais présenté comme valide.
4. **Licences** : revue de presse = extrait ≤ 400 caractères + lien ; pas de contournement de CAPTCHA, d'authentification ou d'anti-bot.
5. Charte Tiadra confinée à `/pulaar/`.
6. Pas de destruction sans migration validée ; ne pas toucher au projet Supabase `le-jacquier-restaurant` (autre client).
7. **Ne pas démarrer un chantier du backlog sans le « go » du propriétaire** (ou un ticket/décision écrite le désignant).
8. Données personnelles : minimum (loi L/2016/037/AN) ; contenu sensible (opinions politiques) ⇒ prudence, modération.

## 5. Cycle de travail obligatoire

**Planifier → construire → tester → déployer → vérifier en production.**

1. *Planifier* : prendre le prochain item du backlog (`PLAN_EVOLUTION` §5 bis, ordre S0, S0b, S1, S2, P1, S3, S4, C1, P2, S7, S5, P3, S6, C2, M1, S8, P4, M2, C3). Vérifier ses dépendances et ses critères de réussite.
2. *Construire* : branche dédiée (§6), changements minimaux, nouvelle app Django pour une nouvelle fonction.
3. *Tester* : `cd v2/site && DJANGO_SETTINGS_MODULE=kaloum24_v2.settings.test python manage.py test kaloum24_v2` et `python manage.py makemigrations --check --dry-run`. Ajouter les tests du nouveau code.
4. *Déployer* : merge/push sur `feat/kaloum24-v2-render`, puis `trigger_deploy` (l'auto-déploiement est peu fiable) et suivre `get_deploy`.
5. *Vérifier* : `/healthz`, `/`, `/actualites/`, la page touchée, logs Render ; si tables nouvelles : `get_advisors` Supabase.
6. *Clore* : mettre à jour `HANDOFF_AGENT.md` (état, pièges) et le miroir Confluence/Project ; cocher l'item du backlog.

**Définition de « fait »** : testé + déployé + vérifié en production + documentation à jour + aucun secret exposé.

## 6. Collaboration sans collision (plusieurs agents/humains)

- **Une branche par chantier** : `agent/<id-item>-<mots-clés>` (ex. `agent/s1-accueil-breves`), créée depuis `feat/kaloum24-v2-render`. Ne jamais forcer un push sur une branche qui n'est pas la tienne.
- **Verrou de chantier** : avant de commencer, ajouter une ligne dans le tableau « Chantiers en cours » de `docs/HANDOFF_AGENT.md` (item, branche, qui, date). La retirer à la fin. Un item verrouillé n'est pas repris par un autre sans accord.
- **Fichiers sensibles aux conflits** (`settings/base.py`, `urls.py`, `INSTALLED_APPS`, migrations) : changements courts, rebase fréquent, une seule migration par app et par PR si possible ; en cas de conflit de migration, régénérer, ne pas fusionner à la main.
- **Un seul déployeur à la fois** : annoncer le déploiement dans la ligne de verrou ; un second agent attend la fin.
- **Commits** : message en français, impératif, préfixe `feat:`/`fix:`/`docs:`/`chore:`/`test:`. Respecter les lignes d'attribution demandées par la session.
- **PR** : titre clair, description = quoi / pourquoi / comment testé / comment vérifié en production / risques.
- **Passation** : en fin de session, laisser dans `HANDOFF_AGENT.md` : ce qui est fait, ce qui reste, les pièges rencontrés, les commandes exactes. Un agent suivant doit pouvoir reprendre sans question.

## 7. Quand s'arrêter et demander

Demander au propriétaire (une question courte) si : décision listée en `PLAN_EVOLUTION` §6 non tranchée ; action irréversible (suppression, rotation de secret, DNS, paiement) ; contenu éditorial sensible ou politique ; toute demande d'accès à un secret ; doute juridique (HAC, données personnelles). Sinon, choisir l'option raisonnable par défaut, l'écrire, et avancer.

## 8. Contrat de communication avec le propriétaire

Français, court, franc. Dire ce qui est fait, ce qui ne l'est pas, et ce qui reste à sa charge. Pas de récit des étapes. Signaler d'emblée toute limite qui change le résultat.

---

# Navigation du code (Graphify, V1)

Avant une question d'architecture, utiliser `graphify query "question"` si
`graphify-out/graph.json` existe et correspond au checkout courant. Vérifier
`graphify-out/provenance.json` ; un graphe ne remplace pas la lecture du code.

Installation de l'outil : `python -m pip install -r requirements-graphify.txt`.
Construction : `python scripts/build_graph.py --output .graphify-ci`.
Le graphe CI couvre le code par AST, sans clé API. Les documents, images et
gabarits demandent une extraction sémantique explicite via la compétence Graphify.

Les relations inférées et les alertes de `diagnostics.json` doivent rester
visibles dans toute conclusion. Confirmer les défauts dans les sources et,
quand possible, par un scénario reproductible. Tests existants :
`python tests_fonctionnels.py` (environnement isolé, base temporaire).
