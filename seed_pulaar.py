"""Amorçage du dictionnaire Pulaar depuis un extrait de Wiktionary.

Charge data_seed_pulaar_wiktionary.json — 22 entrées extraites et vérifiées
manuellement depuis l'API officielle de Wiktionary (Category:Fula lemmas),
traduites en français. Volontairement petit : voir PLAN_PULAAR.md, §A — la
seule source dont la réutilisation est déjà claire (CC BY-SA, attribution
obligatoire), donc on ne prétend pas avoir plus de données qu'on en a.

Ce fichier JSON est figé (pas d'appel réseau à Wiktionary au moment du
seed) : reproductible, ne dépend pas de la disponibilité de Wiktionary au
moment du déploiement.
"""
import json
from pathlib import Path

from extensions import db
from models import PulaarSource, PulaarTerm, PulaarDefinition
from utils import unique_slug

_CHEMIN_DONNEES = Path(__file__).parent / "data_seed_pulaar_wiktionary.json"


def run_seed_pulaar():
    source = PulaarSource.query.filter_by(method="wiktionary").first()
    if not source:
        source = PulaarSource(
            name="Wiktionary (Category:Fula lemmas)",
            url="https://en.wiktionary.org/wiki/Category:Fula_lemmas",
            license="CC BY-SA 4.0 — contenu communautaire Wiktionary, attribution obligatoire",
            method="wiktionary",
        )
        db.session.add(source)
        db.session.flush()

    with open(_CHEMIN_DONNEES, encoding="utf-8") as f:
        entrees = json.load(f)

    crees = 0
    for e in entrees:
        if PulaarTerm.query.filter_by(lemma=e["lemma"]).first():
            continue  # déjà présent, jamais de doublon silencieux

        t = PulaarTerm(
            lemma=e["lemma"], slug=unique_slug(e["lemma"], PulaarTerm),
            part_of_speech=e.get("part_of_speech"), source_id=source.id,
        )
        db.session.add(t)
        db.session.flush()
        db.session.add(PulaarDefinition(term_id=t.id, lang="fr", text=e["definition_fr"]))
        db.session.add(PulaarDefinition(term_id=t.id, lang="en", text=e["definition_en"]))
        crees += 1

    db.session.commit()
    print(f"{crees} terme(s) ajouté(s) depuis Wiktionary "
         f"({len(entrees) - crees} déjà présent(s), ignoré(s)).")
