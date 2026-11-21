from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models.functions import Coalesce
from django.utils.formats import date_format
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from wagtail.admin.panels import FieldPanel, HelpPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.search import index

from wagtail.fields import StreamField
from kaloum24_v2.utils.models import BasePage, ArticleTopic
from kaloum24_v2.utils.blocks import ArticleBody, ArticleImageBlock


class ArticlePage(BasePage):
    template = "pages/article_page.html"
    parent_page_types = ["news.NewsListingPage"]

    author = models.ForeignKey(
        "utils.AuthorSnippet",
        blank=False,
        null=False,
        on_delete=models.deletion.PROTECT,
        related_name="+",
        verbose_name="Signature",
        help_text="Qui signe l'article (une personne ou « Rédaction Kaloum24 »).",
    )
    topic = models.ForeignKey(
        "utils.ArticleTopic",
        blank=False,
        null=False,
        on_delete=models.deletion.PROTECT,
        related_name="article_pages",
        verbose_name="Rubrique",
    )
    publication_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de publication affichée",
        help_text="À remplir seulement pour afficher une autre date que celle de la mise en ligne.",
    )
    dateline = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Lieu",
        help_text="Ville ou lieu d'où vient l'information, par exemple « Conakry » ou « Labé ».",
    )
    introduction = models.TextField(
        blank=True,
        verbose_name="Chapô",
        help_text="Deux ou trois phrases qui résument l'essentiel. Elles apparaissent sous le titre et dans les listes.",
    )
    image = StreamField(
        [("image", ArticleImageBlock())],
        blank=True,
        max_num=1,
        verbose_name="Image principale",
    )
    body = StreamField(ArticleBody(), verbose_name="Texte de l'article")
    sources = RichTextField(
        blank=True,
        features=["bold", "italic", "link", "ul"],
        verbose_name="Sources",
        help_text="D'où viennent les informations : documents, témoins, communiqués, liens. Affiché en bas de l'article.",
    )
    featured_section_title = models.TextField(
        blank=True,
        verbose_name="Titre de la section « À lire aussi »",
    )

    search_fields = BasePage.search_fields + [
        index.SearchField("introduction"),
        index.SearchField("body"),
        index.FilterField("topic"),
    ]

    content_panels = BasePage.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("topic"),
                FieldPanel("author"),
                FieldPanel("dateline"),
                FieldPanel("publication_date"),
            ],
            heading="Rubrique, signature et lieu",
        ),
        FieldPanel("introduction"),
        FieldPanel("image"),
        FieldPanel("body"),
        FieldPanel("sources"),
        MultiFieldPanel(
            [
                FieldPanel("featured_section_title", heading="Titre"),
                InlinePanel(
                    "page_related_pages",
                    label="Article lié",
                    max_num=3,
                ),
            ],
            heading="À lire aussi",
            classname="collapsed",
        ),
    ]

    @property
    def display_date(self):
        if self.publication_date:
            return date_format(self.publication_date, "j F Y")
        elif self.first_published_at:
            return date_format(self.first_published_at, "j F Y")

    @property
    def reading_time(self):
        """Temps de lecture en minutes (200 mots par minute), au moins 1."""
        from django.utils.html import strip_tags

        mots = len(strip_tags(self.introduction or "").split())
        for bloc in self.body:
            if bloc.block_type in ("paragraph", "subheading"):
                mots += len(strip_tags(str(bloc.value)).split())
            elif bloc.block_type == "quote":
                mots += len(str(bloc.value.get("quote", "")).split())
            elif bloc.block_type == "box":
                mots += len(strip_tags(str(bloc.value.get("text", ""))).split())
        return max(1, round(mots / 200))


class NewsListingPage(BasePage):
    template = "pages/news_listing_page.html"
    subpage_types = ["news.ArticlePage"]
    max_count = 1  # Allow only one news listing page to keep article pages in one place

    introduction = RichTextField(blank=True, features=["bold", "italic", "link"])

    search_fields = BasePage.search_fields + [index.SearchField("introduction")]

    content_panels = BasePage.content_panels + [
        FieldPanel("introduction"),
        # FieldPanel("featured_card"),
        HelpPanel("Cette page affiche automatiquement tous les articles publiés qui se trouvent en dessous."),
    ]

    def paginate_queryset(self, queryset, request):
        """Paginate the queryset."""
        page_number = request.GET.get("page", 1)
        paginator = Paginator(queryset, settings.DEFAULT_PER_PAGE)
        try:
            page = paginator.page(page_number)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
        return (paginator, page, page.object_list, page.has_other_pages())

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        queryset = (
            ArticlePage.objects.live()
            .public()
            .annotate(
                date=Coalesce("publication_date", "first_published_at"),
            )
            .select_related("listing_image", "author", "topic")
            .order_by("-date")
        )

        article_topics = (
            ArticleTopic.objects.filter(article_pages__isnull=False)
            .values("title", "slug")
            .distinct()
            .order_by("title")
        )
        matching_topic = False

        topic_query_param = request.GET.get("topic")
        if topic_query_param and topic_query_param in article_topics.values_list(
            "slug", flat=True
        ):
            matching_topic = topic_query_param
            queryset = queryset.filter(topic__slug=topic_query_param)

        # Paginate article pages
        paginator, page, _object_list, is_paginated = self.paginate_queryset(
            queryset, request
        )
        context["paginator"] = paginator
        context["paginator_page"] = page
        context["is_paginated"] = is_paginated

        # Topics
        context["topics"] = article_topics
        context["matching_topic"] = matching_topic

        return context


class Breve(models.Model):
    """Flash info : 1 à 2 phrases horodatées, affichées sur l'accueil. Pas d'article complet."""

    texte = models.CharField("texte", max_length=280, help_text="Une ou deux phrases, 280 caractères au plus.")
    source = models.CharField("source", max_length=120, blank=True, help_text="Qui a fourni l'information.")
    lien = models.URLField("lien", blank=True, help_text="Lien vers la source ou l'article complet (facultatif).")
    publie_le = models.DateTimeField("publiée le", default=timezone.now)
    en_ligne = models.BooleanField("en ligne", default=True)

    class Meta:
        ordering = ["-publie_le"]
        verbose_name = "brève"
        verbose_name_plural = "brèves"

    def __str__(self):
        return self.texte[:60]
