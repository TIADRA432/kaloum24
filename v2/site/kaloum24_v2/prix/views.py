from django.http import Http404
from django.shortcuts import render

from . import services
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
