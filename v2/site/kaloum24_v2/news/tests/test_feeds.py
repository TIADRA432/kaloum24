from datetime import datetime
from xml.etree import ElementTree

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Site

from kaloum24_v2.home.models import HomePage
from kaloum24_v2.news.models import ArticlePage, NewsListingPage
from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet


class LatestArticlesFeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.site = Site.objects.get(is_default_site=True)
        cls.site.hostname = "testserver"
        cls.site.site_name = "Test News"
        cls.site.save()

        cls.home = HomePage.objects.first()
        cls.news_listing = NewsListingPage(
            title="News",
            slug="news",
            introduction="Latest updates from the newsroom.",
            search_description="News feed description",
        )
        cls.home.add_child(instance=cls.news_listing)
        cls.news_listing.save_revision().publish()

        cls.author = AuthorSnippet.objects.create(title="Example Author")
        cls.topic = ArticleTopic.objects.create(title="Technology", slug="technology")

        cls.published_article = ArticlePage(
            title="Published RSS article",
            slug="published-rss-article",
            author=cls.author,
            topic=cls.topic,
            publication_date=timezone.make_aware(datetime(2024, 1, 2, 9, 30)),
            introduction="This article should appear in the RSS feed.",
            listing_summary="Published article summary",
            body=[],
        )
        cls.news_listing.add_child(instance=cls.published_article)
        cls.published_article.save_revision().publish()

        cls.unpublished_article = ArticlePage(
            title="Draft RSS article",
            slug="draft-rss-article",
            author=cls.author,
            topic=cls.topic,
            introduction="This draft should not appear in the RSS feed.",
            body=[],
            live=False,
        )
        cls.news_listing.add_child(instance=cls.unpublished_article)

        from kaloum24_v2.news.feeds import LatestArticlesFeed

        LatestArticlesFeed.site = cls.site
        LatestArticlesFeed.news_listing = cls.news_listing
        cls.feed_url = reverse("news_feed")

    def _feed_xml(self):
        response = self.client.get(self.feed_url)
        return response, ElementTree.fromstring(response.content)

    def test_feed_is_accessible(self):
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/rss+xml", response["Content-Type"])

    def test_feed_returns_rss_2(self):
        _response, root = self._feed_xml()
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.attrib["version"], "2.0")

    def test_feed_title_includes_site_and_listing_titles(self):
        _response, root = self._feed_xml()
        self.assertEqual(root.findtext("channel/title"), "Test News – News")

    def test_feed_includes_published_articles(self):
        _response, root = self._feed_xml()
        channel = root.find("channel")
        item_titles = [item.findtext("title") for item in channel.findall("item")]
        self.assertIn("Published RSS article", item_titles)

    def test_feed_excludes_unpublished_articles(self):
        _response, root = self._feed_xml()
        channel = root.find("channel")
        item_titles = [item.findtext("title") for item in channel.findall("item")]
        self.assertNotIn("Draft RSS article", item_titles)

    def test_feed_item_metadata(self):
        _response, root = self._feed_xml()
        item = root.find("channel/item")
        self.assertEqual(item.findtext("title"), "Published RSS article")
        self.assertEqual(item.findtext("description"), "Published article summary")
        namespaces = {"dc": "http://purl.org/dc/elements/1.1/"}
        self.assertEqual(
            item.findtext("dc:creator", namespaces=namespaces), "Example Author"
        )
        self.assertEqual(item.findtext("category"), "Technology")
        self.assertIn("/news/published-rss-article/", item.findtext("link"))
        self.assertIn("/news/published-rss-article/", item.findtext("guid"))
        self.assertIsNotNone(item.findtext("pubDate"))


class TopicFeedTests(LatestArticlesFeedTests):
    def test_flux_par_rubrique(self):
        r = self.client.get(reverse("news_feed_topic", args=["technology"]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Published RSS article")
        self.assertContains(r, "Technology")

    def test_rubrique_inconnue(self):
        self.assertEqual(self.client.get("/news/feed/inconnue/").status_code, 404)

    def test_page_liste_des_flux(self):
        r = self.client.get("/flux-rss/")
        self.assertContains(r, "/news/feed/technology/")
