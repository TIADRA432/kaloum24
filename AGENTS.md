# Kaloum24 — navigation du code

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
