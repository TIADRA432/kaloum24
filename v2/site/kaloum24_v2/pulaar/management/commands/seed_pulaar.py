"""Amorçage du dictionnaire depuis le JSON figé extrait de Wiktionary.

22 entrées (Category:Fula lemmas, CC BY-SA, attribution obligatoire), traduites
en français. Volontairement petit : la seule source dont la réutilisation est
déjà claire. Idempotent, sans appel réseau : reproductible à chaque déploiement.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from kaloum24_v2.pulaar.models import PulaarDefinition, PulaarSource, PulaarTerm

DONNEES = Path(__file__).resolve().parents[2] / "data" / "wiktionary.json"


class Command(BaseCommand):
    help = "Charge les termes Pulaar issus de Wiktionary (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        source, _ = PulaarSource.objects.get_or_create(
            method="wiktionary",
            defaults={
                "name": "Wiktionary (Category:Fula lemmas)",
                "url": "https://en.wiktionary.org/wiki/Category:Fula_lemmas",
                "license": "CC BY-SA 4.0 — attribution obligatoire",
            },
        )
        entrees = json.loads(DONNEES.read_text(encoding="utf-8"))
        crees = 0
        for e in entrees:
            if PulaarTerm.objects.filter(lemma=e["lemma"]).exists():
                continue
            terme = PulaarTerm(lemma=e["lemma"], part_of_speech=e.get("part_of_speech", ""), source=source)
            terme.save()
            PulaarDefinition.objects.create(term=terme, lang="fr", text=e["definition_fr"])
            PulaarDefinition.objects.create(term=terme, lang="en", text=e["definition_en"])
            crees += 1
        self.stdout.write(f"{crees} terme(s) ajouté(s), {len(entrees) - crees} déjà présent(s).")
