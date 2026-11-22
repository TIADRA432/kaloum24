"""Contrôle des règles du dictionnaire. Code de sortie 1 s'il y a une violation."""
from django.core.management.base import BaseCommand

from kaloum24_v2.pulaar.models import (
    PulaarEntry, PulaarExternalDictionary, PulaarSense, PulaarSource, PulaarTranslation,
)


def verifier():
    """Renvoie (violations, infos) : listes de messages."""
    violations, infos = [], []
    for e in PulaarEntry.objects.filter(status=PulaarEntry.VALIDE):
        if not e.senses.exclude(text="").exists():
            violations.append(f"Entrée validée sans définition en pulaar : {e.lemma} (n° {e.pk})")
    for d in PulaarExternalDictionary.objects.all():
        if d.url_for("x") is None:
            violations.append(f"Dictionnaire externe au modèle non sûr : {d.code}")
    for s in PulaarSense.objects.filter(text=""):
        violations.append(f"Sens vide sur l'entrée n° {s.entry_id}")
    cachees = PulaarEntry.objects.exclude(source__rights_status__in=PulaarSource.PUBLIABLES).count()
    if cachees:
        infos.append(f"{cachees} entrée(s) non affichées au public (droits de la source non établis).")
    sans_sens = PulaarEntry.objects.filter(senses__isnull=True).count()
    infos.append(f"{sans_sens} entrée(s) sans définition en pulaar (à définir).")
    infos.append(f"{PulaarTranslation.objects.filter(is_validated=False).count()} traduction(s) non vérifiée(s).")
    return violations, infos


class Command(BaseCommand):
    help = "Vérifie les règles du dictionnaire (validé ⇒ définition pulaar, liens externes sûrs…)."

    def handle(self, *args, **options):
        violations, infos = verifier()
        for m in infos:
            self.stdout.write(f"info : {m}")
        for m in violations:
            self.stderr.write(f"VIOLATION : {m}")
        if violations:
            raise SystemExit(1)
        self.stdout.write("Dictionnaire conforme.")
