from unittest import mock

from django.test import TestCase
from django.urls import reverse

from kaloum24_v2.news import presse
from kaloum24_v2.news.models import ArticlePresse, SourcePresse

FLUX = """<?xml version="1.0"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
<item><title>Titre &eacute;t&eacute;</title><link>https://exemple.test/a</link>
<description>&lt;p&gt;%s&lt;/p&gt;&lt;p&gt;L'article X est apparu en premier sur Y.&lt;/p&gt;</description>
<pubDate>Sat, 21 Nov 2026 10:00:00 +0000</pubDate></item>
<item><title>Sans lien</title><link>pas-un-lien</link></item>
</channel></rss>""" % ("mot " * 300)


class PresseTests(TestCase):
    def setUp(self):
        self.src = SourcePresse.objects.create(nom="Test", site="https://exemple.test", flux="https://exemple.test/feed")

    def test_lecture_extrait_et_entites(self):
        entrees = presse.lire_flux(FLUX.encode())
        self.assertEqual(len(entrees), 1)
        titre, extrait, lien, _ = entrees[0]
        self.assertEqual(titre, "Titre été")
        self.assertLessEqual(len(extrait), 400)
        self.assertTrue(extrait.endswith("…"))
        self.assertNotIn("apparu en premier", extrait)

    def test_collecte_sans_doublon(self):
        with mock.patch.object(presse, "telecharger", return_value=FLUX.encode()):
            self.assertEqual(presse.collecter(), 1)
            self.assertEqual(presse.collecter(), 0)
        self.assertEqual(ArticlePresse.objects.count(), 1)

    def test_panne_sans_erreur(self):
        with mock.patch.object(presse, "telecharger", side_effect=OSError("403")):
            self.assertEqual(presse.collecter(), 0)
        self.src.refresh_from_db()
        self.assertIn("403", self.src.derniere_erreur)

    def test_page_et_source_desactivee(self):
        ArticlePresse.objects.create(source=self.src, titre="Un titre", lien="https://exemple.test/1", publie_le="2026-11-21T10:00:00Z")
        r = self.client.get(reverse("revue_de_presse"))
        self.assertContains(r, "Un titre")
        self.assertContains(r, 'target="_blank"')
        self.src.actif = False
        self.src.save()
        self.assertNotContains(self.client.get(reverse("revue_de_presse")), "Un titre")
