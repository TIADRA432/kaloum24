import json

from django.core.management import call_command
from django.test import TestCase

from kaloum24_v2.news.management.commands.publier_articles import DOSSIER
from kaloum24_v2.news.models import ArticlePage, NewsListingPage
from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet

FICHIER = DOSSIER / "alkule-latin-potndinaade.json"


class PublierArticlesTests(TestCase):
    def setUp(self):
        call_command("init_kaloum24", verbosity=0)
        self.doc = json.loads(FICHIER.read_text(encoding="utf-8"))

    def test_creation_et_publication(self):
        call_command("publier_articles", verbosity=0)
        page = ArticlePage.objects.get(slug=self.doc["slug"])
        self.assertTrue(page.live)
        self.assertEqual(page.topic.title, "Pulaar")
        r = self.client.get(page.url)
        self.assertEqual(r.status_code, 200)
        for attendu in ("Alkule laaɓɗe (Voyelles)", "<table", "baaba", "Batu Niamey (1978)", "min de lecture"):
            self.assertContains(r, attendu)
        # Rien du matériel de l'assistant ne doit se retrouver dans l'article.
        for interdit in ("Wagtail", "JSON / HTML", "Geɗe kuutorteeɗe", "Ɓanndu Winndannde"):
            self.assertNotContains(r, interdit)

    def test_page_existante_remplacee_avec_redirection(self):
        listing = NewsListingPage.objects.get()
        autre = AuthorSnippet.objects.create(title="Une autre signature")
        ancienne = ArticlePage(
            title=self.doc["title"], slug=self.doc["ancien_slug"], topic=ArticleTopic.objects.get(title="Société"),
            author=autre, introduction="brouillon", body=json.dumps([{"type": "paragraph", "value": "<p>vieux</p>"}]),
        )
        listing.add_child(instance=ancienne)
        ancienne.save_revision().publish()

        call_command("publier_articles", verbosity=0)
        self.assertEqual(ArticlePage.objects.count(), 1)  # pas de doublon
        page = ArticlePage.objects.get()
        self.assertEqual(page.pk, ancienne.pk)
        self.assertEqual(page.slug, self.doc["slug"])
        self.assertEqual(page.author, autre)  # signature et rubrique conservées
        self.assertEqual(page.topic.title, "Société")
        self.assertEqual(page.introduction, self.doc["introduction"])
        self.assertIn("table", [b.block_type for b in page.body])
        self.assertGreater(page.revisions.count(), 1)  # l'historique est conservé
        r = self.client.get(f"{listing.url}{self.doc['ancien_slug']}/")
        self.assertIn(r.status_code, (301, 302))
        self.assertEqual(self.client.get(page.url).status_code, 200)

    def test_import_unique_ne_reecrit_pas_le_travail_de_l_equipe(self):
        call_command("publier_articles", verbosity=0)
        page = ArticlePage.objects.get(slug=self.doc["slug"])
        page.introduction = "Corrigé par la rédaction"
        page.save_revision().publish()
        call_command("publier_articles", verbosity=0)
        page.refresh_from_db()
        self.assertEqual(page.introduction, "Corrigé par la rédaction")
        self.assertEqual(ArticlePage.objects.count(), 1)
