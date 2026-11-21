from django.core.management.base import BaseCommand

from kaloum24_v2.prix import change


class Command(BaseCommand):
    help = "Importe le dernier cours de référence de la BCRG (PDF officiel) pour le convertisseur."

    def handle(self, *args, **opts):
        n = change.importer()
        self.stdout.write(f"{n} cours ajouté(s).")
