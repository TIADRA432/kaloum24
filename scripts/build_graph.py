"""Reconstruit le graphe du code sans importer ni exécuter l'application Flask."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.detect import detect, save_manifest
from graphify.diagnostics import diagnose_extraction, format_diagnostic_report
from graphify.export import to_json
from graphify.extract import extract
from graphify.report import generate

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def build(output, semantic=None, labels_file=None, force=False):
    out = output.resolve() / "graphify-out"
    out.mkdir(parents=True, exist_ok=True)
    detection = detect(ROOT)
    code_files = [Path(f) for f in detection["files"]["code"]]
    if not code_files:
        raise SystemExit("Aucun fichier de code détecté.")
    extraction = extract(code_files, cache_root=output.resolve(), root=ROOT, max_workers=2)
    if semantic:
        sem = json.loads(semantic.read_text(encoding="utf-8"))
        known = {n["id"] for n in extraction["nodes"]}
        for node in sem["nodes"]:
            if node["id"] not in known:
                extraction["nodes"].append(node)
                known.add(node["id"])
        extraction["edges"].extend(sem["edges"])
        extraction["hyperedges"] = sem.get("hyperedges", [])
        extraction["input_tokens"] = sem.get("input_tokens", 0)
        extraction["output_tokens"] = sem.get("output_tokens", 0)
    graph = build_from_json(extraction, root=str(ROOT), directed=False)
    if not graph.number_of_nodes():
        raise SystemExit("Extraction vide : aucun résultat publié.")
    communities = cluster(graph)
    cohesion = score_all(graph, communities)
    labels = {cid: " / ".join(dict.fromkeys(
        Path(graph.nodes[n].get("source_file", "code")).stem
        for n in sorted(nodes, key=lambda n: graph.degree(n), reverse=True)
    ))[:90] for cid, nodes in communities.items()}
    if labels_file:
        labels.update({int(k): v for k, v in json.loads(labels_file.read_text(encoding="utf-8")).items()})
    if not to_json(graph, communities, str(out / "graph.json"), community_labels=labels, force=force):
        raise SystemExit("Graphify refuse de remplacer un graphe plus grand. Utiliser un dossier de sortie neuf.")
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)
    tokens = {"input": extraction.get("input_tokens", 0), "output": extraction.get("output_tokens", 0)}
    report = generate(graph, communities, cohesion, labels, gods, surprises,
                      detection, tokens, str(ROOT), suggested_questions=questions)
    scope = "code + extraction sémantique fournie" if semantic else "code uniquement (AST), sans analyse sémantique des documents/images/gabarits"
    report += "\n\n## Périmètre de cette exécution\n\n" + scope + ".\n"
    if semantic:
        report += "Les compteurs de jetons sémantiques ne sont pas disponibles dans l'outil de délégation ; zéro ne représente pas le coût réel.\n"
    (out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    diagnostic = diagnose_extraction(extraction, directed=False, root=str(ROOT))
    write_json(out / "diagnostics.json", diagnostic)
    print(format_diagnostic_report(diagnostic))
    write_json(out / ".graphify_extract.json", extraction)
    write_json(out / ".graphify_detect.json", detection)
    write_json(out / ".graphify_labels.json", {str(k): v for k, v in labels.items()})
    write_json(out / ".graphify_analysis.json", {"communities": communities, "cohesion": cohesion, "gods": gods, "surprises": surprises, "questions": questions})
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    write_json(out / "provenance.json", {
        "commit": commit, "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graphify_version": importlib.metadata.version("graphifyy"), "scope": scope,
        "code_files": len(code_files), "nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(),
        "communities": len(communities), "skipped_sensitive": detection.get("skipped_sensitive", []),
        "semantic_token_usage": "unavailable" if semantic else "not applicable",
    })
    (out / ".graphify_python").write_text(sys.executable, encoding="utf-8")
    (out / ".graphify_root").write_text(str(ROOT), encoding="utf-8")
    if graph.number_of_nodes() > 5000:
        print("Attention : plus de 5 000 nœuds ; visualisation agrégée par Graphify.")
    subprocess.run([sys.executable, "-m", "graphify", "export", "html", "--graph", str(out / "graph.json"), "--labels", str(out / ".graphify_labels.json")], cwd=output.resolve(), check=True)
    if not (out / "graph.html").is_file():
        raise SystemExit("La visualisation HTML manque.")
    from graphify.cli import _stamped_manifest_files
    manifest = _stamped_manifest_files(detection["files"], extraction, ROOT)
    save_manifest(manifest, root=str(ROOT), scan_corpus={f for files in detection["files"].values() for f in files})
    print(f"Graph complete: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges, {len(communities)} communities → {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--semantic", type=Path, help="Extraction sémantique vérifiée pour ce checkout seulement")
    parser.add_argument("--labels", type=Path, help="Noms de communautés validés pour cette extraction")
    parser.add_argument("--force", action="store_true", help="Autoriser explicitement un graphe plus petit après suppression/exclusion de code")
    args = parser.parse_args()
    build(args.output, args.semantic, args.labels, args.force)
