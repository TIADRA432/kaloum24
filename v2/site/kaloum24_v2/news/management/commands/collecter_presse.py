from django.core.management.base import BaseCommand

from kaloum24_v2.news import presse


class Command(BaseCommand):
    help = "Collecte les titres des sources de presse actives (extrait + lien)."

    def handle(self, *args, **options):
        n = presse.collecter()
        self.stdout.write(f"Revue de presse : {n} nouveau(x) titre(s).")
