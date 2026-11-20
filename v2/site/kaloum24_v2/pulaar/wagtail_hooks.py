"""Administration du dictionnaire dans Wagtail (snippets) : rien à coder pour
ajouter un terme, un domaine ou modérer une proposition."""
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import PulaarDomain, PulaarProposal, PulaarSource, PulaarTerm


class TermViewSet(SnippetViewSet):
    model = PulaarTerm
    icon = "doc-full"
    menu_label = "Termes"
    list_display = ["lemma", "part_of_speech", "status", "domain", "source"]
    list_filter = ["status", "domain"]
    search_fields = ["lemma", "definitions__text"]
    panels = [
        FieldPanel("lemma"),
        FieldPanel("part_of_speech"),
        FieldPanel("domain"),
        FieldPanel("source"),
        FieldPanel("status"),
        InlinePanel("definitions", label="Définition", min_num=1),
    ]


class DomainViewSet(SnippetViewSet):
    model = PulaarDomain
    icon = "folder-open-inverse"
    menu_label = "Domaines"
    panels = [FieldPanel("name")]


class SourceViewSet(SnippetViewSet):
    model = PulaarSource
    icon = "link"
    menu_label = "Sources"
    list_display = ["name", "license", "method"]
    panels = [FieldPanel("name"), FieldPanel("url"), FieldPanel("license"), FieldPanel("method")]


class ProposalViewSet(SnippetViewSet):
    model = PulaarProposal
    icon = "comment"
    menu_label = "Propositions à relire"
    list_display = ["term_lemma", "status", "contributor_name", "created_at"]
    list_filter = ["status"]
    search_fields = ["term_lemma", "definition_ff", "definition_fr"]
    panels = [
        FieldPanel("status"),
        FieldPanel("term_lemma"),
        FieldPanel("definition_ff"),
        FieldPanel("definition_fr"),
        FieldPanel("domain"),
        FieldPanel("justification"),
        MultiFieldPanel([FieldPanel("contributor_name"), FieldPanel("contributor_contact")],
                        heading="Contributeur (non public)"),
    ]


class PulaarGroup(SnippetViewSetGroup):
    items = [TermViewSet, DomainViewSet, SourceViewSet, ProposalViewSet]
    menu_icon = "globe"
    menu_label = "Dictionnaire Pulaar"
    menu_name = "pulaar"
    menu_order = 300


register_snippet(PulaarGroup)
