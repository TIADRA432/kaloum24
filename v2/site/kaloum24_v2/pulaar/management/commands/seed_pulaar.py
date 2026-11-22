"""Amorçage du dictionnaire : données de RÉFÉRENCE (dialectes, classes grammaticales,
dictionnaires externes) puis les 22 entrées du JSON figé extrait de Wiktionary.

- Dialectes : codes ISO 639-3 (fuf, fuc, ffm, fue, fuh, fuq, fuv, fub, fui) + « ful »
  (macro-langue, variété non précisée). Aucune valeur inventée.
- Wiktionary (Category:Fula lemmas, CC BY-SA, attribution obligatoire) ne précise pas
  la variété : les entrées sont rattachées à « ful ». Les gloses fr/en sont des
  TRADUCTIONS (jamais des définitions : le dictionnaire est monolingue pulaar) ; ces
  entrées n'ont donc pas encore de définition en pulaar.
- Idempotent, sans appel réseau.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from kaloum24_v2.pulaar.models import (
    PulaarDialect, PulaarEntry, PulaarExternalDictionary, PulaarPos, PulaarSource, PulaarTranslation,
)

DONNEES = Path(__file__).resolve().parents[2] / "data" / "wiktionary.json"

DIALECTES = [  # (code ISO 639-3, nom, région) — d'après l'ISO 639-3 / Ethnologue
    ("ful", "Peul — variété non précisée", "macro-langue (ISO 639-3 : ful)"),
    ("fuf", "Pular — Fuuta Jaloo", "Guinée, Sierra Leone"),
    ("fuc", "Pulaar — Fuuta Tooro", "Sénégal, Gambie, Mauritanie"),
    ("ffm", "Fulfulde — Maasina", "Mali, Ghana"),
    ("fue", "Fulfulde — Borgu", "Bénin, Togo"),
    ("fuh", "Fulfulde — Niger occidental", "Burkina Faso, Niger"),
    ("fuq", "Fulfulde — Niger centre-oriental", "Niger"),
    ("fuv", "Fulfulde — Nigéria", "Nigéria"),
    ("fub", "Fulfulde — Adamaoua", "Cameroun, Tchad, Nigéria"),
    ("fui", "Fulfulde — Bagirmi", "Centrafrique"),
]

# Liste de départ, modifiable dans l'admin. Noms français uniquement : aucun nom
# pulaar n'est inventé (name_ff reste vide jusqu'à ce qu'un locuteur le fournisse).
CLASSES = [
    ("nom", "Nom", False), ("verbe", "Verbe", True), ("adjectif", "Adjectif", False),
    ("adverbe", "Adverbe", False), ("pronom", "Pronom", False), ("conjonction", "Conjonction", False),
    ("interjection", "Interjection", False), ("numeral", "Numéral", False), ("particule", "Particule", False),
    ("a-preciser", "À préciser", False),
]

DICTIONNAIRES_EXTERNES = [
    ("wiktionnaire-fr", "Wiktionnaire (français)", "fra", "https://fr.wiktionary.org/wiki/{term}"),
    ("wiktionary-en", "Wiktionary (English)", "eng", "https://en.wiktionary.org/wiki/{term}"),
]


class Command(BaseCommand):
    help = "Charge les données de référence et les entrées issues de Wiktionary (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, nom, region in DIALECTES:
            PulaarDialect.objects.get_or_create(code=code, defaults={"name": nom, "region": region})
        for code, nom, verbal in CLASSES:
            PulaarPos.objects.get_or_create(code=code, defaults={"name_fr": nom, "is_verbal": verbal})
        for code, nom, langue, modele in DICTIONNAIRES_EXTERNES:
            PulaarExternalDictionary.objects.get_or_create(
                code=code, defaults={"name": nom, "language_code": langue, "url_template": modele})

        source, cree = PulaarSource.objects.get_or_create(
            method="wiktionary",
            defaults={
                "name": "Wiktionary (Category:Fula lemmas)",
                "url": "https://en.wiktionary.org/wiki/Category:Fula_lemmas",
                "license": "CC BY-SA 4.0 — attribution obligatoire",
                "rights_status": PulaarSource.LIBRE,
                "rights_note": "Licence libre CC BY-SA : attribution et partage dans les mêmes conditions.",
            },
        )
        # Source déjà présente avant l'ajout du statut de droits : elle a reçu « à vérifier ».
        # La licence de Wiktionary est connue (CC BY-SA) : on ne corrige que ce défaut, jamais
        # un statut choisi ensuite par un humain.
        if not cree and source.rights_status == PulaarSource.A_VERIFIER:
            source.rights_status = PulaarSource.LIBRE
            source.rights_note = "Licence libre CC BY-SA : attribution et partage dans les mêmes conditions."
            source.save(update_fields=["rights_status", "rights_note"])
        dialecte = PulaarDialect.objects.get(code="ful")
        classes = {p.code: p for p in PulaarPos.objects.all()}
        entrees = json.loads(DONNEES.read_text(encoding="utf-8"))
        crees = 0
        for e in entrees:
            pos = classes.get(e.get("part_of_speech", ""), classes["a-preciser"])
            if PulaarEntry.objects.filter(dialect=dialecte, lemma=e["lemma"], pos=pos).exists():
                continue
            entree = PulaarEntry(lemma=e["lemma"], dialect=dialecte, pos=pos, source=source)
            entree.save()
            PulaarTranslation.objects.create(entry=entree, language_code="fra", term=e["definition_fr"], source=source)
            PulaarTranslation.objects.create(entry=entree, language_code="eng", term=e["definition_en"], source=source)
            crees += 1
        self.stdout.write(f"{crees} entrée(s) ajoutée(s), {len(entrees) - crees} déjà présente(s).")
