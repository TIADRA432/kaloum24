import json
import os

from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_GET


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


@require_GET
def manifeste(request):
    """Manifeste d'application web : permet d'installer Kaloum24 sur l'écran d'accueil du téléphone."""
    donnees = {
        "name": "Kaloum24", "short_name": "Kaloum24", "lang": "fr", "dir": "ltr",
        "description": "L'actualité de Guinée et d'Afrique de l'Ouest, rédigée à Conakry.",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#FFFFFF", "theme_color": "#1E2B63",
        "icons": [
            {"src": static("home/icones/icone-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("home/icones/icone-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("home/icones/maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return HttpResponse(json.dumps(donnees, ensure_ascii=False), content_type="application/manifest+json")


@require_GET
def service_worker(request):
    """Service worker à la racine (portée « / ») : pages déjà vues lisibles sans réseau, page de secours."""
    version = (os.environ.get("RENDER_GIT_COMMIT") or "dev")[:8]
    precache = [static(p) for p in ("css/main.css", "home/k24.css", "home/vie.css", "home/accueil.css",
                                    "home/fonts/unbounded-600.woff2", "home/fonts/charis-400.woff2")]
    reponse = render(request, "sw.js", {"version": version, "precache": json.dumps(precache)}, content_type="application/javascript")
    reponse["Cache-Control"] = "no-cache"
    return reponse


def hors_ligne(request):
    return render(request, "pages/hors_ligne.html")
