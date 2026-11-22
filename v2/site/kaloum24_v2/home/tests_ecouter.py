from django.core.files.base import ContentFile
from django.test import TestCase


class EcouterTests(TestCase):
    def setUp(self):
        from kaloum24_v2.home.models import HomePage
        from kaloum24_v2.news.models import ArticlePage, NewsListingPage
        from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet

        liste = NewsListingPage(title="Actus", slug="actus-test", introduction="x")
        HomePage.objects.first().add_child(instance=liste)
        liste.save_revision().publish()
        self.article = ArticlePage(
            title="Un titre", slug="un-titre", introduction="Le chapô.", body=[],
            author=AuthorSnippet.objects.create(title="A"),
            topic=ArticleTopic.objects.create(title="T", slug="t"),
        )
        liste.add_child(instance=self.article)
        self.article.save_revision().publish()

    def test_bouton_ecouter_sans_audio(self):
        r = self.client.get(self.article.url)
        self.assertContains(r, "data-ecouter-lire")
        self.assertContains(r, 'id="art-corps"')
        self.assertContains(r, "ecouter.js")
        self.assertNotContains(r, "<audio")

    def test_lecteur_audio_si_fichier(self):
        from wagtail.documents.models import Document

        d = Document.objects.create(title="Voix", file=ContentFile(b"ID3", name="voix.mp3"))
        self.article.audio = d
        self.article.save_revision().publish()
        r = self.client.get(self.article.url)
        self.assertContains(r, "<audio")
        self.assertContains(r, "Version audio")
        self.assertNotContains(r, "data-ecouter-lire")


class ImagesRubriqueTests(TestCase):
    def test_photos_en_bas_de_la_liste_des_actualites(self):
        from kaloum24_v2.home.models import HomePage
        from kaloum24_v2.news.models import NewsListingPage

        liste = NewsListingPage(title="Actus", slug="actus-img", introduction="x")
        HomePage.objects.first().add_child(instance=liste)
        liste.save_revision().publish()
        html = self.client.get(liste.url).content.decode()
        self.assertIn("La Guinée en images", html)
        self.assertIn("Crédits des images", html)
