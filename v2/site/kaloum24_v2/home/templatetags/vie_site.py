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


@register.filter
def ambiance(slug):
    """Numéro d'ambiance (0-5) stable pour une rubrique : même rubrique, même décor."""
    return sum(ord(c) for c in (slug or "tout")) % 6


@register.simple_tag
def chiffres_du_jour():
    """Prix de quelques denrées de base (médiane des marchés, dernier mois connu) pour l'accueil."""
    try:
        from kaloum24_v2.prix import services
        from kaloum24_v2.prix.models import Produit

        sortie = []
        for p in Produit.objects.filter(a_la_une=True):
            r = services.resume(p)
            if r:
                sortie.append({"produit": p, **r})
        return sortie
    except Exception:
        return []


@register.simple_tag
def illustrations():
    """Photos libres de droits (Wikimedia Commons) avec auteur, licence et lien : credits.json à côté des images."""
    import json
    from pathlib import Path

    try:
        chemin = Path(__file__).resolve().parents[1] / "static" / "home" / "illustrations" / "credits.json"
        return json.loads(chemin.read_text(encoding="utf-8"))
    except Exception:
        return []


# Pictogrammes dessinés pour Kaloum24 (aucune photo, aucun droit tiers). Traits indigo + aplat ocre.
_ICONES = {
    "sac": '<path d="M20 12c-4 4-9 8-9 20v20c0 4 3 7 7 7h28c4 0 7-3 7-7V32c0-12-5-16-9-20z" fill="#F7E7C8" stroke="currentColor" stroke-width="3"/><path d="M20 12c4 3 8 3 12 0 4 3 8 3 12 0" fill="none" stroke="currentColor" stroke-width="3"/>%s',
    "bouteille": '<path d="M26 6h12v10l5 8v32c0 2-2 4-4 4H25c-2 0-4-2-4-4V24l5-8z" fill="#E08A2E" fill-opacity=".35" stroke="currentColor" stroke-width="3"/><path d="M21 36h22" stroke="currentColor" stroke-width="3"/>',
    "pain": '<path d="M8 34c0-12 10-20 24-20s24 8 24 20c0 4-2 6-5 6v8H13v-8c-3 0-5-2-5-6z" fill="#E08A2E" fill-opacity=".5" stroke="currentColor" stroke-width="3"/><path d="M22 22l4 8M32 20l4 8M42 22l4 8" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',
    "oignon": '<path d="M32 8c2 6 2 9 0 12M32 20c14 4 20 14 14 26-4 6-24 6-28 0-6-12 0-22 14-26z" fill="#E08A2E" fill-opacity=".4" stroke="currentColor" stroke-width="3"/><path d="M32 22c-6 8-6 20 0 28M32 22c6 8 6 20 0 28" fill="none" stroke="currentColor" stroke-width="2"/>',
    "tomate": '<circle cx="32" cy="36" r="20" fill="#E08A2E" fill-opacity=".55" stroke="currentColor" stroke-width="3"/><path d="M22 20l10 6 10-6M32 12v14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',
    "aubergine": '<path d="M22 22c-8 10-6 28 4 34 8 4 18-2 22-12 2-6-2-10-8-14l-4-12z" fill="#2B3A7A" fill-opacity=".55" stroke="currentColor" stroke-width="3"/><path d="M36 18c0-6 4-8 8-8" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',
    "haricot": '<path d="M12 44c2-18 18-30 40-30 0 20-14 36-34 36-4 0-6-2-6-6z" fill="#F7E7C8" stroke="currentColor" stroke-width="3"/><circle cx="26" cy="36" r="3.5" fill="currentColor"/><circle cx="36" cy="28" r="3.5" fill="currentColor"/><circle cx="44" cy="22" r="3.5" fill="currentColor"/>',
    "arachide": '<path d="M24 10c8-4 16 2 14 12 6 4 6 12 0 16 2 10-6 16-14 14-8-4-8-14-2-18-6-4-4-12 2-24z" fill="#E08A2E" fill-opacity=".4" stroke="currentColor" stroke-width="3" transform="rotate(25 32 32)"/>',
    "poisson": '<path d="M6 32c10-14 28-14 38 0-10 14-28 14-38 0zM44 32l14-10v20z" fill="#E08A2E" fill-opacity=".4" stroke="currentColor" stroke-width="3" stroke-linejoin="round"/><circle cx="18" cy="29" r="2.5" fill="currentColor"/>',
    "viande": '<path d="M14 24c4-10 24-14 34-6 8 8 2 24-10 28-12 4-28-2-24-22z" fill="#9A2B14" fill-opacity=".45" stroke="currentColor" stroke-width="3"/><circle cx="38" cy="30" r="5" fill="#F7E7C8" stroke="currentColor" stroke-width="3"/>',
    "piment": '<path d="M16 22c14-8 34-2 34 14 0 8-6 14-16 16 8-6 4-16-6-18-6-1-10-6-12-12z" fill="#9A2B14" fill-opacity=".55" stroke="currentColor" stroke-width="3" stroke-linejoin="round"/><path d="M16 22c-2-6 2-10 6-10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',
    "patate": '<path d="M12 36c-2-14 12-22 26-20 12 2 16 12 12 22-4 10-14 12-24 10-8-2-13-4-14-12z" fill="#E08A2E" fill-opacity=".35" stroke="currentColor" stroke-width="3"/><circle cx="26" cy="30" r="1.8" fill="currentColor"/><circle cx="38" cy="38" r="1.8" fill="currentColor"/><circle cx="34" cy="26" r="1.8" fill="currentColor"/>',
    "panier": '<path d="M10 28h44l-5 24H15z" fill="#F7E7C8" stroke="currentColor" stroke-width="3" stroke-linejoin="round"/><path d="M20 28c0-12 6-18 12-18s12 6 12 18" fill="none" stroke="currentColor" stroke-width="3"/>',
}
_SACS = {  # marque posée sur le sac : grains, cubes, cristaux
    "grains": '<g fill="currentColor"><ellipse cx="24" cy="38" rx="3" ry="1.6"/><ellipse cx="34" cy="34" rx="3" ry="1.6"/><ellipse cx="42" cy="42" rx="3" ry="1.6"/><ellipse cx="28" cy="48" rx="3" ry="1.6"/><ellipse cx="38" cy="50" rx="3" ry="1.6"/></g>',
    "cubes": '<g fill="#fff" stroke="currentColor" stroke-width="2"><rect x="22" y="34" width="9" height="9"/><rect x="33" y="40" width="9" height="9"/><rect x="26" y="45" width="8" height="8"/></g>',
    "cristaux": '<g fill="none" stroke="currentColor" stroke-width="2"><path d="M24 40l4-4 4 4-4 4zM36 46l4-4 4 4-4 4zM30 52l3-3 3 3-3 3z"/></g>',
}
_PAR_CODE = {
    "Rice (imported)": ("sac", "grains"), "Rice (local)": ("sac", "grains"), "Sugar": ("sac", "cubes"), "Salt": ("sac", "cristaux"),
    "Maize": ("sac", "grains"), "Fonio": ("sac", "grains"), "Cassava meal (gari)": ("sac", "grains"),
    "Oil (vegetable)": ("bouteille", None), "Oil (palm)": ("bouteille", None), "Bread": ("pain", None),
    "Onions (imported)": ("oignon", None), "Tomatoes": ("tomate", None), "Eggplants": ("aubergine", None),
    "Beans (niebe, white)": ("haricot", None), "Groundnuts (shelled)": ("arachide", None),
    "Fish": ("poisson", None), "Fish (dry)": ("poisson", None), "Meat (beef)": ("viande", None),
    "Chili (red, dry raw)": ("piment", None), "Potatoes": ("patate", None),
}


@register.simple_tag
def icone_produit(produit):
    """Petit pictogramme (SVG en ligne, décoratif) pour un produit du suivi des prix."""
    from django.utils.safestring import mark_safe

    nom, marque = _PAR_CODE.get(getattr(produit, "code", ""), ("panier", None))
    corps = _ICONES[nom]
    if "%s" in corps:
        corps = corps % (_SACS.get(marque, "") if marque else "")
    return mark_safe(f'<svg class="px-ico" viewBox="0 0 64 64" width="56" height="56" aria-hidden="true" focusable="false">{corps}</svg>')
