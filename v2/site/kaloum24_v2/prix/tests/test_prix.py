from datetime import date

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from kaloum24_v2.prix import services
from kaloum24_v2.prix.management.commands.importer_prix_pam import Command
from kaloum24_v2.prix.models import Lieu, Observation, Produit

ENTETE = "date,admin1,admin2,market,market_id,latitude,longitude,category,commodity,commodity_id,unit,priceflag,pricetype,currency,price,usdprice\n"


def ligne(d, marche, prix, produit="Rice (imported)"):
    return f"{d},Kankan,Kankan,{marche},1,0,0,cereals,{produit},71,KG,actual,Retail,GNF,{prix},0.5\n"


class PrixTests(TestCase):
    def test_import_idempotent_et_filtre(self):
        auj = date.today().replace(day=1)
        csv_ = ENTETE + ligne(auj, "A", 100) + ligne(auj, "B", 300) + ligne(auj, "A", 999, "Inconnu") + "#meta,x\n"
        self.assertEqual(Command.importer(csv_), 2)
        self.assertEqual(Command.importer(csv_), 0)
        self.assertEqual(Observation.objects.count(), 2)

    def test_mediane_variation_et_pages(self):
        p = Produit.objects.create(code="X", nom="Riz test", unite="kg", a_la_une=True)
        a, b, c = (Lieu.objects.create(nom=n) for n in "ABC")
        for m, prix in ((date(2025, 11, 1), (100, 100, 100)), (date(2026, 11, 1), (100, 120, 200))):
            for lieu, v in zip((a, b, c), prix):
                Observation.objects.create(produit=p, lieu=lieu, date=m, prix=v)
        r = services.resume(p)
        self.assertEqual(r["prix"], 120)  # médiane, pas moyenne
        self.assertEqual(r["v12"], 20.0)
        self.assertEqual(r["marches"], 3)
        self.assertContains(self.client.get(reverse("prix")), "Riz test")
        page = self.client.get(reverse("prix_produit", args=[p.pk]))
        self.assertContains(page, "CC BY-IGO")
        self.assertContains(page, "<svg")
        self.assertEqual(self.client.get(reverse("prix_produit", args=[9999])).status_code, 404)

    def test_courbe_trop_courte(self):
        self.assertEqual(services.courbe_svg([(date(2026, 1, 1), 1, 1)]), "")
