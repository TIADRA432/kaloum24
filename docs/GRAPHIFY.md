# Graphify pour Kaloum24

Graphify est une dépendance de développement, séparée du serveur Flask et
épinglée dans `requirements-graphify.txt`.

```bash
python -m pip install -r requirements-graphify.txt
python scripts/build_graph.py --output .graphify-ci
graphify query "checkout subscription webhook" --graph .graphify-ci/graphify-out/graph.json
```

Le workflow `.github/workflows/graphify.yml` reconstruit le graphe à chaque
push, pull request et lancement manuel. Il publie un artefact
`graphify-<SHA>` conservé 30 jours : graphe interactif HTML, JSON, rapport,
diagnostics et provenance du commit. Ouvrir GitHub → Actions → Graphify →
exécution concernée → Artifacts. Télécharger et décompresser ; ouvrir
`graph.html` dans un navigateur. Les artefacts privés exigent une connexion.
Un second job exécute les tests fonctionnels existants sous Linux.

Les résultats sont attachés à chaque exécution, sans commit automatique du
bot et sans boucle de génération. Le job a seulement `contents: read` et ne
reçoit aucune clé de l'application. Les versions d'Actions suivent les
versions majeures officielles ; la version de Graphify est fixe.

## Couverture et limites

La CI analyse le code par AST sans LLM. Elle ne lance pas Flask, ne contacte
pas Stripe/Meta et ne constitue pas un audit de sécurité. Une modification
d'un document déclenche aussi le job mais son sens n'est pas réinterprété.
Les fichiers tiers sous `static/vendor/` sont exclus. Graphify applique aussi
ses filtres de fichiers sensibles ; consulter `provenance.json` pour les omissions.

L'audit initial ajoute une extraction sémantique des documents, gabarits et
visuels avec la compétence Graphify. Ce graphe complet est disponible localement
dans `graphify-out/`. Pour le reproduire, relancer cette compétence ; ne pas
réutiliser une ancienne extraction sémantique après modification des sources.

Un graphe non orienté fusionne certaines relations entre les mêmes nœuds.
`diagnostics.json` expose les pertes et références sans cible résolue ; ne pas
interpréter l'absence d'une arête comme une preuve d'absence de dépendance.
La provenance signale les modifications locales non commitées.

Un dossier de sortie neuf permet les reconstructions après suppression de
code : Graphify refuse par défaut d'écraser un graphe plus grand. En CI, chaque
checkout est neuf. Localement, choisir un autre `--output` pour ce cas.

Références : [setup-python](https://github.com/actions/setup-python),
[upload-artifact](https://github.com/actions/upload-artifact).
