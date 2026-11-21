from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Breve



@hooks.register("register_log_actions")
def enregistrer_actions(actions):
    actions.register_action("kaloum24.import", "Import d'un article", "Article importé depuis un fichier")


class BreveViewSet(SnippetViewSet):
    model = Breve
    icon = "bold"
    menu_label = "Brèves"
    menu_order = 210
    add_to_admin_menu = True
    list_display = ["texte", "source", "publie_le", "en_ligne"]
    list_filter = ["en_ligne"]
    search_fields = ["texte", "source"]


register_snippet(BreveViewSet)
