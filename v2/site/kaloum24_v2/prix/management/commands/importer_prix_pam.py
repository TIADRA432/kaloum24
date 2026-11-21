"""Importe les prix de détail du PAM (HDX, licence CC BY-IGO) pour la Guinée. Idempotent.

Source : https://data.humdata.org/dataset/wfp-food-prices-for-guinea — fichier CSV mis à jour par le PAM.
"""
import csv
import io
import json
import urllib.request
from datetime import date, datetime

from django.core.management.base import BaseCommand

from kaloum24_v2.prix.models import Lieu, Observation, Produit

PAQUET = "https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-guinea"
AGENT = {"User-Agent": "Kaloum24/1.0 (+https://kaloum24.onrender.com)"}
# code d'origine → (nom français, unité, ordre, sur l'accueil)
PRODUITS = {
    "Rice (imported)": ("Riz importé", "kg", 1, True), "Rice (local)": ("Riz local", "kg", 2, True),
    "Oil (vegetable)": ("Huile végétale", "litre", 3, True), "Sugar": ("Sucre", "kg", 4, True),
    "Oil (palm)": ("Huile de palme", "litre", 5, False), "Onions (imported)": ("Oignons importés", "kg", 6, False),
    "Bread": ("Pain", "pièce", 7, False), "Maize": ("Maïs", "kg", 8, False),
    "Cassava meal (gari)": ("Gari (farine de manioc)", "kg", 9, False), "Fonio": ("Fonio", "kg", 10, False),
    "Potatoes": ("Pommes de terre", "kg", 11, False), "Tomatoes": ("Tomates", "kg", 12, False),
    "Eggplants": ("Aubergines", "kg", 13, False), "Beans (niebe, white)": ("Niébé (haricot blanc)", "kg", 14, False),
    "Groundnuts (shelled)": ("Arachides décortiquées", "kg", 15, False), "Fish": ("Poisson frais", "kg", 16, False),
    "Fish (dry)": ("Poisson séché", "kg", 17, False), "Meat (beef)": ("Viande de bœuf", "kg", 18, False),
    "Chili (red, dry raw)": ("Piment rouge sec", "kg", 19, False), "Salt": ("Sel", "kg", 20, True),
}
DEPUIS = 36  # mois conservés


def url_csv():
    with urllib.request.urlopen(urllib.request.Request(PAQUET, headers=AGENT), timeout=30) as r:  # noqa: S310
        res = json.load(r)["result"]["resources"]
    return next(x["url"] for x in res if x["name"].lower().startswith("guinea - food prices"))


class Command(BaseCommand):
    help = "Importe les prix de détail du PAM pour la Guinée (20 produits, ~15 marchés)."

    def add_arguments(self, parser):
        parser.add_argument("--fichier", help="CSV local (tests, hors ligne)")

    def handle(self, *args, **opts):
        if opts["fichier"]:
            contenu = open(opts["fichier"], encoding="utf-8").read()
        else:
            with urllib.request.urlopen(urllib.request.Request(url_csv(), headers=AGENT), timeout=60) as r:  # noqa: S310
                contenu = r.read().decode("utf-8")
        n = self.importer(contenu)
        self.stdout.write(f"Prix PAM : {n} nouveau(x) relevé(s).")

    @staticmethod
    def importer(contenu):
        auj = date.today()
        limite = date(auj.year - DEPUIS // 12, auj.month, 1)
        produits = {}
        for code, (nom, unite, ordre, une) in PRODUITS.items():
            p, cree = Produit.objects.get_or_create(code=code, defaults={"nom": nom, "unite": unite, "ordre": ordre, "a_la_une": une})
            if not cree and p.a_la_une != une:
                p.a_la_une = une
                p.save(update_fields=["a_la_une"])
            produits[code] = p
        lieux, a_creer = {}, {}
        existants = set(Observation.objects.filter(date__gte=limite).values_list("produit_id", "lieu_id", "date"))
        for ligne in csv.DictReader(io.StringIO(contenu)):
            if ligne["date"].startswith("#") or ligne["commodity"] not in produits:
                continue
            if ligne["pricetype"] != "Retail" or ligne["currency"] != "GNF":
                continue
            d = datetime.strptime(ligne["date"], "%Y-%m-%d").date().replace(day=1)
            if d < limite:
                continue
            nom_marche = ligne["market"]
            if nom_marche not in lieux:
                lieux[nom_marche], _ = Lieu.objects.get_or_create(nom=nom_marche, defaults={"region": ligne["admin1"]})
            cle = (produits[ligne["commodity"]].pk, lieux[nom_marche].pk, d)
            if cle not in existants and cle not in a_creer:
                a_creer[cle] = Observation(produit=produits[ligne["commodity"]], lieu=lieux[nom_marche], date=d, prix=ligne["price"])
        Observation.objects.bulk_create(a_creer.values(), batch_size=1000, ignore_conflicts=True)
        return len(a_creer)
