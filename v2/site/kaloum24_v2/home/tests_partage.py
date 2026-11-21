from django.test import TestCase


class PartageTests(TestCase):
    def test_pages_de_service_ont_un_apercu(self):
        for url, titre in (("/meteo/", "Météo"), ("/revue-de-presse/", "Revue de presse"), ("/convertisseur/", "Convertisseur de devises")):
            r = self.client.get(url)
            self.assertContains(r, f'<meta property="og:title" content="{titre}">', html=False)
            self.assertContains(r, 'property="og:image"')
            self.assertContains(r, "partage")  # image par défaut
            self.assertContains(r, 'rel="canonical"')
            self.assertContains(r, 'name="twitter:card"')

    def test_accueil_a_une_description(self):
        r = self.client.get("/")
        self.assertContains(r, 'property="og:description"')
        self.assertContains(r, 'property="og:site_name" content="Kaloum24"')


class PartageArticleTests(TestCase):
    def test_description_article_vient_du_chapo(self):
        from kaloum24_v2.home.models import HomePage
        from kaloum24_v2.news.models import ArticlePage, NewsListingPage
        from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet

        liste = NewsListingPage(title="Actus", slug="actus-test", introduction="x")
        HomePage.objects.first().add_child(instance=liste)
        liste.save_revision().publish()
        art = ArticlePage(title="Un titre", slug="un-titre", introduction="Le chapô de l'article.", body=[],
                          author=AuthorSnippet.objects.create(title="A"), topic=ArticleTopic.objects.create(title="T", slug="t"))
        liste.add_child(instance=art)
        art.save_revision().publish()
        r = self.client.get(art.url)
        self.assertContains(r, "Le chapô de l&#x27;article.")
        self.assertContains(r, 'og:type" content="article"')
