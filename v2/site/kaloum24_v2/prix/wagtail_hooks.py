from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Observation, Produit, TauxChange


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


class TauxChangeViewSet(SnippetViewSet):
    model = TauxChange
    icon = "doc-full"
    menu_label = "Cours de change (BCRG)"
    menu_order = 255
    add_to_admin_menu = True
    list_display = ["date", "devise", "cours"]
    list_filter = ["devise"]


register_snippet(ProduitViewSet)
register_snippet(TauxChangeViewSet)
register_snippet(ObservationViewSet)
