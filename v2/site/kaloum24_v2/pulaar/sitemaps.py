from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import PulaarEntry


class PulaarSitemap(Sitemap):
    """Page d'accueil du dictionnaire + une entrée par terme publié."""

    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return ["accueil", *PulaarEntry.objects.publiques().order_by("lemma")]

    def location(self, item):
        if item == "accueil":
            return reverse("pulaar:accueil")
        return reverse("pulaar:terme", args=[item.slug])
