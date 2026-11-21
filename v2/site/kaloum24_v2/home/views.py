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


def flux_rss(request):
    """Liste des flux RSS : tous les articles, puis un flux par rubrique."""
    from kaloum24_v2.utils.models import ArticleTopic

    return render(request, "pages/flux_rss.html", {"rubriques": ArticleTopic.objects.order_by("title")})
