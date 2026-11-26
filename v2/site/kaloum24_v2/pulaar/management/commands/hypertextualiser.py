"""Calcule les liens des définitions (colonne `text_html`) : migration des données existantes et rattrapage.

  hypertextualiser                  sens jamais calculés ou calculés par une ancienne version (build Render)
  hypertextualiser --tout           tout recalculer : fréquences, mots-outils automatiques, tous les sens
  hypertextualiser --sens 12 13     seulement ces sens
  hypertextualiser --simuler        calcule et compte, n'écrit rien
  hypertextualiser --rapport --paires g:w,f:p
                                    mesure ce que des alternances d'initiales retrouveraient (n'écrit rien)
"""
import time

from django.core.management.base import BaseCommand

from kaloum24_v2.pulaar import liens
from kaloum24_v2.pulaar.models import PulaarStopword


class Command(BaseCommand):
    help = "Hypertextualise les définitions du dictionnaire pulaar."

    def add_arguments(self, p):
        p.add_argument("--tout", action="store_true")
        p.add_argument("--sens", nargs="+", type=int)
        p.add_argument("--simuler", action="store_true")
        p.add_argument("--seuil", type=int, help="occurrences au-delà desquelles un mot n'est plus lié (défaut 500)")
        p.add_argument("--rapport", action="store_true")
        p.add_argument("--paires", default="", help="ex. g:w,f:p (hypothèses à mesurer, jamais appliquées)")

    def handle(self, *a, **o):
        debut = time.time()
        if o["rapport"]:
            paires = [tuple(x.split(":", 1)) for x in o["paires"].split(",") if ":" in x]
            if not paires:
                self.stdout.write("Donne des paires à mesurer : --rapport --paires g:w,f:p")
                return
            for r in liens.rapport_mutations(paires):
                ex = ", ".join(f"{f}→{c} ({n})" for f, n, c in r["exemples"])
                self.stdout.write(f"{r['paire']} : {r['mots']} mots, {r['occurrences']} occurrences. Exemples : {ex}")
            self.stdout.write("Mesure seulement : rien n'est activé. Faire valider les paires par un lexicographe.")
            return
        if o["sens"]:
            n, nb = liens.relier_sens(o["sens"], simuler=o["simuler"])
        elif o["tout"] and not o["simuler"]:
            r = liens.recalculer_tout(o["seuil"])
            n, nb = r["sens"], r["liens"]
            self.stdout.write(f"{r['mots_outils']} mots trop fréquents laissés sans lien (automatique).")
        elif o["tout"]:
            n, nb = liens.relier_sens(tous=True, simuler=True)
        elif not PulaarStopword.objects.exists():
            # Premier passage (ou liste vidée) : le seuil de fréquence n'a jamais été calculé, on fait tout.
            r = liens.recalculer_tout(o["seuil"])
            n, nb = r["sens"], r["liens"]
            self.stdout.write(f"Premier calcul : {r['mots_outils']} mots trop fréquents laissés sans lien.")
        else:
            n, nb = liens.relier_en_retard()
        s = liens.stats()
        self.stdout.write(self.style.SUCCESS(
            f"{n} définition(s) traitée(s), {nb} lien(s){' (simulation)' if o['simuler'] else ''} en {time.time() - debut:.1f} s. "
            f"Au total : {s['avec_liens']}/{s['sens']} définitions avec au moins un lien."))
