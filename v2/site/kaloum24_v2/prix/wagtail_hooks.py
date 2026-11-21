from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Observation, Produit


class ProduitViewSet(SnippetViewSet):
    model = Produit
    icon = "tag"
    menu_label = "Produits (prix)"
    menu_order = 240
    add_to_admin_menu = True
    list_display = ["nom", "unite", "ordre", "a_la_une"]


class ObservationViewSet(SnippetViewSet):
    model = Observation
    icon = "list-ul"
    menu_label = "Relevés de prix"
    menu_order = 250
    add_to_admin_menu = True
    list_display = ["produit", "lieu", "date", "prix"]
    list_filter = ["produit", "lieu"]


register_snippet(ProduitViewSet)
register_snippet(ObservationViewSet)
