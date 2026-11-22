"""Administration du dictionnaire dans Wagtail (snippets) : rien à coder pour
ajouter une entrée, une traduction, une source ou relire une proposition."""
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import (
    PulaarDialect, PulaarDomain, PulaarEntry, PulaarExternalDictionary, PulaarNounClass, PulaarPos,
    PulaarProposal, PulaarSource,
)


class EntryViewSet(SnippetViewSet):
    model = PulaarEntry
    icon = "doc-full"
    menu_label = "Entrées"
    list_display = ["lemma", "dialect", "pos", "status", "source"]
    list_filter = ["status", "dialect", "pos", "domain"]
    search_fields = ["lemma", "senses__text", "translations__term"]
    panels = [
        MultiFieldPanel(
            [FieldPanel("lemma"), FieldPanel("dialect"), FieldPanel("pos"), FieldPanel("homonym_index"),
             FieldPanel("noun_class"), FieldPanel("domain")],
            heading="Le mot",
        ),
        InlinePanel("senses", label="Sens (définition en pulaar)"),
        InlinePanel("pronunciations", label="Prononciation (API)", classname="collapsed"),
        InlinePanel("audios", label="Enregistrement audio", classname="collapsed"),
        InlinePanel("images", label="Illustration", classname="collapsed"),
        InlinePanel("variants", label="Forme variante", classname="collapsed"),
        InlinePanel("examples", label="Exemple", classname="collapsed"),
        InlinePanel("translations", label="Traduction", classname="collapsed"),
        InlinePanel("relations", label="Lien vers une autre entrée (synonyme, contraire, dérivé…)", classname="collapsed"),
        MultiFieldPanel(
            [FieldPanel("origin"), FieldPanel("origin_language"), FieldPanel("etymology"), FieldPanel("usage_note")],
            heading="Origine, étymologie et usage (à remplir par le lexicographe)", classname="collapsed",
        ),
        MultiFieldPanel([FieldPanel("source"), FieldPanel("status")], heading="Provenance et statut"),
    ]


class DialectViewSet(SnippetViewSet):
    model = PulaarDialect
    icon = "site"
    menu_label = "Dialectes"
    list_display = ["name", "code", "region"]
    panels = [FieldPanel("code"), FieldPanel("name"), FieldPanel("region")]


class PosViewSet(SnippetViewSet):
    model = PulaarPos
    icon = "list-ul"
    menu_label = "Classes grammaticales"
    list_display = ["name_fr", "name_ff", "is_verbal"]
    panels = [FieldPanel("code"), FieldPanel("name_fr"), FieldPanel("name_ff"), FieldPanel("is_verbal")]


class NounClassViewSet(SnippetViewSet):
    model = PulaarNounClass
    icon = "tag"
    menu_label = "Classes nominales"
    list_display = ["marker", "dialect"]
    panels = [FieldPanel("marker"), FieldPanel("dialect"), FieldPanel("note")]


class DomainViewSet(SnippetViewSet):
    model = PulaarDomain
    icon = "folder-open-inverse"
    menu_label = "Domaines"
    panels = [FieldPanel("name")]


class SourceViewSet(SnippetViewSet):
    model = PulaarSource
    icon = "link"
    menu_label = "Sources"
    list_display = ["name", "rights_status", "license", "method"]
    list_filter = ["rights_status"]
    panels = [FieldPanel("name"), FieldPanel("url"), FieldPanel("license"), FieldPanel("method"),
              FieldPanel("rights_status"), FieldPanel("rights_note")]


class ExternalDictionaryViewSet(SnippetViewSet):
    model = PulaarExternalDictionary
    icon = "link-external"
    menu_label = "Dictionnaires externes"
    list_display = ["name", "language_code", "url_template"]
    panels = [FieldPanel("code"), FieldPanel("name"), FieldPanel("language_code"),
              FieldPanel("url_template"), FieldPanel("notes")]


class ProposalViewSet(SnippetViewSet):
    model = PulaarProposal
    icon = "comment"
    menu_label = "Propositions à relire"
    list_display = ["term_lemma", "status", "contributor_name", "created_at"]
    list_filter = ["status"]
    search_fields = ["term_lemma", "definition_ff", "translation_fr"]
    panels = [
        FieldPanel("status"),
        FieldPanel("term_lemma"),
        FieldPanel("definition_ff"),
        FieldPanel("translation_fr"),
        FieldPanel("dialect"),
        FieldPanel("pos"),
        FieldPanel("domain"),
        FieldPanel("justification"),
        MultiFieldPanel([FieldPanel("contributor_name"), FieldPanel("contributor_contact")],
                        heading="Contributeur (non public)"),
    ]


class PulaarGroup(SnippetViewSetGroup):
    items = [EntryViewSet, ProposalViewSet, SourceViewSet, DialectViewSet, PosViewSet, NounClassViewSet,
             ExternalDictionaryViewSet, DomainViewSet]
    menu_icon = "globe"
    menu_label = "Dictionnaire Pulaar"
    menu_name = "pulaar"
    menu_order = 300


register_snippet(PulaarGroup)


from django.urls import path, reverse  # noqa: E402
from wagtail import hooks  # noqa: E402
from wagtail.admin.menu import MenuItem  # noqa: E402

from . import admin_views  # noqa: E402


@hooks.register("register_admin_urls")
def urls_import():
    return [
        path("dictionnaire-pulaar/tableau/", admin_views.tableau, name="pulaar_tableau"),
        path("dictionnaire-pulaar/tableau/classe/", admin_views.tableau_classe, name="pulaar_tableau_classe"),
        path("dictionnaire-pulaar/import/", admin_views.import_lot, name="pulaar_import"),
        path("dictionnaire-pulaar/import/<int:pk>/retirer/", admin_views.retirer, name="pulaar_import_retirer"),
    ]


class ImportMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_perm("pulaar.add_pulaarimportbatch")


class TableauMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_perm("pulaar.change_pulaarentry")


@hooks.register("register_admin_menu_item")
def menu_tableau():
    return TableauMenuItem("Tableau de bord du dictionnaire", reverse("pulaar_tableau"), icon_name="list-ul", order=305)


@hooks.register("register_admin_menu_item")
def menu_import():
    return ImportMenuItem("Importer un lot (dictionnaire)", reverse("pulaar_import"), icon_name="upload", order=310)


def _avertir_droits(request, instance):
    """Rend visible l'effet d'un changement de droits : une source « publiable » ouvre ses entrées au public."""
    from django.contrib import messages
    if isinstance(instance, PulaarSource) and instance.pk:
        n = instance.entries.count()
        if instance.is_publishable and n:
            messages.warning(
                request,
                f"Attention : « {instance.name} » est en « {instance.get_rights_status_display()} » — ses {n} entrée(s) "
                "sont désormais visibles de tout le monde. Repasse en « À vérifier » si l'autorisation de l'auteur "
                "n'est pas établie.")
        elif n:
            messages.info(request, f"Les {n} entrée(s) de cette source ne sont pas visibles du public (droits non établis).")


@hooks.register("after_edit_snippet")
def apres_modification_source(request, instance):
    _avertir_droits(request, instance)
