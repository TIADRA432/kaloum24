from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Page

from kaloum24_v2.news.models import NewsListingPage
from kaloum24_v2.utils.models import ArticleTopic


class InitKaloum24Tests(TestCase):
    def test_initialisation_idempotente_sans_contenu_invente(self):
        call_command("init_kaloum24", verbosity=0)
        call_command("init_kaloum24", verbosity=0)
        self.assertEqual(NewsListingPage.objects.count(), 1)
        self.assertEqual(ArticleTopic.objects.count(), 7)
        # Aucun article inventé : seules la racine, l'accueil et « Actualités ».
        self.assertEqual(Page.objects.count(), 3)

    def test_pages_publiques(self):
        call_command("init_kaloum24", verbosity=0)
        for url in ("/", "/actualites/", "/pulaar/", "/healthz", "/search/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get("/"), "Dictionnaire pulaar")
        self.assertContains(self.client.get("/"), 'lang="fr"')

    def test_admin_exige_connexion(self):
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/login/", r["Location"])


class ImageParDefautTests(TestCase):
    def test_fichier_perdu_est_restaure(self):
        import tempfile

        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from django.test import override_settings

        from kaloum24_v2.images.models import CustomImage

        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            from io import BytesIO

            from PIL import Image

            tampon = BytesIO()
            Image.new("RGB", (10, 10), "white").save(tampon, "PNG")
            image = CustomImage(title="Placeholder Image")
            image.file.save("Placeholder_Image.png", ContentFile(tampon.getvalue()), save=False)
            image.width = image.height = 10
            image.save()
            image.tags.add("placeholder")
            nom = image.file.name
            default_storage.delete(nom)  # le disque éphémère a tout perdu
            self.assertFalse(default_storage.exists(nom))
            call_command("init_kaloum24", verbosity=0)
            image.refresh_from_db()
            self.assertTrue(default_storage.exists(image.file.name))
            self.assertGreater(default_storage.size(image.file.name), 1000)


class IndexationTests(TestCase):
    def setUp(self):
        call_command("init_kaloum24", verbosity=0)
        call_command("seed_pulaar", verbosity=0)

    def test_robots_ouvert_et_ferme_admin(self):
        from django.test import override_settings

        with override_settings(SEO_NOINDEX=False):
            r = self.client.get("/robots.txt")
            self.assertContains(r, "Disallow: /admin/")
            self.assertContains(r, "Sitemap: http")
            self.assertNotContains(r, "Disallow: /\n")
        with override_settings(SEO_NOINDEX=True):
            self.assertContains(self.client.get("/robots.txt"), "Disallow: /\n")

    def test_sitemap_pages_et_termes(self):
        r = self.client.get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "/actualites/")
        self.assertContains(r, "/pulaar/terme/aada/")


class ImageParDefautCreationTests(TestCase):
    def test_creation_a_la_volee_porte_une_extension(self):
        from kaloum24_v2.utils.models import SystemMessagesSettings
        from wagtail.models import Site

        call_command("init_kaloum24", verbosity=0)
        reglages = SystemMessagesSettings.for_site(Site.objects.get(is_default_site=True))
        image = reglages.get_placeholder_image()
        self.assertTrue(image.file.name.endswith(".webp"), image.file.name)
