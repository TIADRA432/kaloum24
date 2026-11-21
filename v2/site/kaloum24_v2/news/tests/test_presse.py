from unittest import mock

from django.test import TestCase
from django.utils import timezone
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
        titre, extrait, lien, _, image = entrees[0]
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


class ImageTests(TestCase):
    def test_extraction_image(self):
        flux = """<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>A</title><link>https://e.test/a</link><media:thumbnail url="https://e.test/img/a.webp"/></item>
<item><title>B</title><link>https://e.test/b</link><description>&lt;p&gt;&lt;img src="https://e.test/b.jpg" /&gt;Texte&lt;/p&gt;</description></item>
<item><title>C</title><link>https://e.test/c</link><description>&lt;img src="http://e.test/non-https.jpg"&gt;</description></item>
<item><title>D</title><link>https://e.test/d</link><description>&lt;img src="https://secure.gravatar.com/x.jpg"&gt;</description></item>
</channel></rss>"""
        imgs = [e[4] for e in presse.lire_flux(flux.encode())]
        self.assertEqual(imgs, ["https://e.test/img/a.webp", "https://e.test/b.jpg", "", ""])


class LangueTests(TestCase):
    def test_source_fulfulde_marquee(self):
        from kaloum24_v2.news.models import ArticlePresse, SourcePresse

        s = SourcePresse.objects.create(nom="RFI Fulfulde", site="https://www.rfi.fr/ff/", flux="https://www.rfi.fr/ff/rss", langue="ff")
        ArticlePresse.objects.create(source=s, titre="Kabaruuji", lien="https://www.rfi.fr/ff/x", publie_le=timezone.now())
        r = self.client.get("/revue-de-presse/")
        self.assertContains(r, 'lang="ff"')
        self.assertContains(r, "Fulfulde")


class ImagePageTests(TestCase):
    def test_og_image_extraite(self):
        class R:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s, n): return b'<html><head><meta property="og:image" content="https://exemple.gn/photo.jpg" /></head>'

        with mock.patch("urllib.request.urlopen", return_value=R()):
            self.assertEqual(presse.image_de_page("https://exemple.gn/a"), "https://exemple.gn/photo.jpg")

    def test_og_image_refuse_logo_et_http(self):
        class R:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s, n): return b'<meta property="og:image" content="http://exemple.gn/logo.png">'

        with mock.patch("urllib.request.urlopen", return_value=R()):
            self.assertEqual(presse.image_de_page("https://exemple.gn/a"), "")

    def test_panne_reseau_silencieuse(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("boom")):
            self.assertEqual(presse.image_de_page("https://exemple.gn/a"), "")


class FiltreImageTests(TestCase):
    def test_photo_au_nom_pixel_acceptee_mais_pas_le_pixel_de_suivi(self):
        self.assertIsNone(presse.RE_PAS_ILLUSTRATION.search("https://x.gn/IMG_1200_x_630_pixel.webp"))
        self.assertTrue(presse.RE_PAS_ILLUSTRATION.search("https://x.gn/pixel.gif"))
        self.assertTrue(presse.RE_PAS_ILLUSTRATION.search("https://x.gn/logo-site.png"))
