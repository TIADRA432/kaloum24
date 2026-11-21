from django.db import models
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.search import index

from wagtail.fields import StreamField
from kaloum24_v2.utils.blocks import StoryBlock, InternalLinkBlock
from kaloum24_v2.utils.models import BasePage


class HomePage(BasePage):
    template = "pages/home_page.html"
    introduction = models.TextField(blank=True)
    hero_cta = StreamField(
        [("link", InternalLinkBlock())],
        blank=True,
        min_num=0,
        max_num=1,
    )
    body = StreamField(StoryBlock())
    featured_section_title = models.TextField(blank=True)

    search_fields = BasePage.search_fields + [index.SearchField("introduction")]

    content_panels = BasePage.content_panels + [
        FieldPanel("introduction"),
        FieldPanel("hero_cta"),
        FieldPanel("body"),
        MultiFieldPanel(
            [
                FieldPanel("featured_section_title", heading="Title"),
                InlinePanel(
                    "page_related_pages",
                    label="Pages",
                    max_num=12,
                ),
            ],
            heading="Featured section",
        ),
    ]


    def get_context(self, request, *args, **kwargs):
        from django.db.models.functions import Coalesce

        from kaloum24_v2.news.models import ArticlePage, Breve
        from kaloum24_v2.pulaar.models import mot_du_jour
        from kaloum24_v2.utils.models import ArticleTopic

        context = super().get_context(request, *args, **kwargs)
        articles = (
            ArticlePage.objects.live().public()
            .annotate(date=Coalesce("publication_date", "first_published_at"))
            .select_related("listing_image", "author", "topic")
            .order_by("-date")
        )
        recents = list(articles[:10])
        context["une"] = recents[0] if recents else None
        context["secondaires"] = recents[1:4]
        context["dernieres"] = recents[4:10]
        context["breves"] = list(Breve.objects.filter(en_ligne=True)[:6])
        par_rubrique = []
        for rubrique in ArticleTopic.objects.filter(article_pages__isnull=False).distinct().order_by("title"):
            items = list(articles.filter(topic=rubrique)[:3])
            if items:
                par_rubrique.append({"rubrique": rubrique, "articles": items})
        context["par_rubrique"] = par_rubrique
        context["mot_du_jour"] = mot_du_jour()
        from kaloum24_v2.news.models import NewsListingPage

        context["listing"] = NewsListingPage.objects.live().first()
        return context
