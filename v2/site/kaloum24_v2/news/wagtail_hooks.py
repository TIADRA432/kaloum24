from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import ArticlePresse, Breve, SourcePresse



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


class SourcePresseViewSet(SnippetViewSet):
    model = SourcePresse
    icon = "site"
    menu_label = "Sources de presse"
    menu_order = 220
    add_to_admin_menu = True
    list_display = ["nom", "actif", "derniere_collecte", "derniere_erreur"]
    list_filter = ["actif"]


class ArticlePresseViewSet(SnippetViewSet):
    model = ArticlePresse
    icon = "doc-full"
    menu_label = "Titres de presse"
    menu_order = 230
    add_to_admin_menu = True
    list_display = ["titre", "source", "publie_le", "visible"]
    list_filter = ["visible", "source"]
    search_fields = ["titre"]


register_snippet(SourcePresseViewSet)
register_snippet(ArticlePresseViewSet)
