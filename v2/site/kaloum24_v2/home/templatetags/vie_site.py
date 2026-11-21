from django import template
from django.core.cache import cache
from django.db.models.functions import Coalesce

register = template.Library()


@register.inclusion_tag("components/bandeau-vivant.html")
def bandeau_vivant():
    """Barre d'info présente sur toutes les pages : date et heure de Conakry (JS),
    flash info défilant, météo. Uniquement des données réelles du site."""
    from kaloum24_v2.home.meteo import meteo
    from kaloum24_v2.news.models import ArticlePage, Breve

    items = cache.get("bandeau:items")
    if items is None:
        items = [{"texte": b.texte, "heure": b.publie_le, "lien": b.lien, "type": "breve"}
                 for b in Breve.objects.filter(en_ligne=True)[:8]]
        recents = (ArticlePage.objects.live().public()
                   .annotate(date=Coalesce("publication_date", "first_published_at"))
                   .order_by("-date")[:5])
        items += [{"texte": a.title, "lien": a.url, "type": "article"} for a in recents]
        cache.set("bandeau:items", items, 60)
    villes = meteo()
    return {"items": items, "meteo": villes[:1], "duree": max(25, 9 * len(items))}


@register.simple_tag
def meteo_villes():
    from kaloum24_v2.home.meteo import meteo
    return meteo()


@register.simple_tag
def pied_liens():
    """Pages cadre publiées (À propos, Mentions légales, Charte…) pour le pied de page : apparaissent seules à leur publication."""
    from wagtail.models import Site

    from kaloum24_v2.standardpages.models import StandardPage

    try:
        racine = Site.objects.get(is_default_site=True).root_page
        return list(StandardPage.objects.child_of(racine).live().order_by("path"))
    except Exception:  # jamais d'erreur 500 pour un pied de page
        return []
