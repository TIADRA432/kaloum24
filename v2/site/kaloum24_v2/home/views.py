from django.shortcuts import render


def credits_images(request):
    return render(request, "pages/credits_images.html")


def meteo_page(request):
    """Météo de toutes les villes suivies, regroupées par pays (même service, même cache que l'accueil)."""
    from .meteo import meteo

    groupes = {}
    for v in meteo():
        groupes.setdefault(v.get("pays", ""), []).append(v)
    return render(request, "pages/meteo.html", {"groupes": groupes.items(), "vide": not groupes})
