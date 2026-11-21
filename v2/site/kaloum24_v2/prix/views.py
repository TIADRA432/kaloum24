from django.http import Http404
from django.shortcuts import render

from decimal import Decimal, InvalidOperation

from . import change, services
from .models import Produit


def accueil(request):
    lignes = []
    for p in Produit.objects.all():
        r = services.resume(p)
        if r:
            lignes.append({"produit": p, **r})
    return render(request, "pages/prix.html", {"lignes": lignes, "mois": lignes[0]["date"] if lignes else None})


def produit(request, pk):
    try:
        p = Produit.objects.get(pk=pk)
    except Produit.DoesNotExist:
        raise Http404
    r = services.resume(p)
    if not r:
        raise Http404
    return render(request, "pages/prix_produit.html", {
        "produit": p, "r": r, "courbe": services.courbe_svg(r["serie"]), "marches": services.par_marche(p)})


def convertisseur(request):
    """Convertisseur GNF / devises au cours de référence de la BCRG (date et source affichées)."""
    change.rafraichir_si_perime()
    jour, cours, source = change.derniers_cours()
    noms = {"GNF": "Franc guinéen (GNF)", **{c: change.DEVISES[c] for c in cours}}
    de, vers = request.GET.get("de", "EUR"), request.GET.get("vers", "GNF")
    brut = request.GET.get("montant", "1").replace(" ", "").replace("\u00a0", "").replace(",", ".")
    resultat, erreur = None, ""
    try:
        montant = Decimal(brut)
        if montant < 0 or montant > Decimal("1e12"):
            raise InvalidOperation
        resultat = change.convertir(montant, de, vers, cours)
        if resultat is None and cours:
            erreur = "Devise inconnue."
    except InvalidOperation:
        montant, erreur = None, "Entrez un montant valide, par exemple 100 ou 2500,50."
    return render(request, "pages/convertisseur.html", {
        "jour": jour, "source": source, "devises": list(noms.items()), "de": de, "vers": vers,
        "montant": request.GET.get("montant", "1"), "resultat": resultat, "erreur": erreur,
        "pret": bool(cours), "montant_num": montant if not erreur else None,
        "taux_de": cours.get(de, Decimal(1)) if de != "GNF" else Decimal(1)})
