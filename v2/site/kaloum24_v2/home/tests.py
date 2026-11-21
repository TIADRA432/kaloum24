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
        self.assertEqual(ArticleTopic.objects.count(), 11)
        # Aucun article inventé : racine, accueil, « Actualités » et 3 pages cadre en brouillon.
        self.assertEqual(Page.objects.count(), 6)
        self.assertEqual(Page.objects.filter(live=False).count(), 3)

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


class RolesTests(TestCase):
    def test_roles_en_francais_limites_aux_actualites(self):
        from django.contrib.auth.models import Group
        from wagtail.models import GroupPagePermission, Workflow

        call_command("init_kaloum24", verbosity=0)
        self.assertFalse(Group.objects.filter(name__in=["Editors", "Moderators"]).exists())
        redacteurs = Group.objects.get(name="Rédacteurs")
        relecteurs = Group.objects.get(name="Relecteurs")
        listing = NewsListingPage.objects.get()

        def droits(groupe):
            return set(GroupPagePermission.objects.filter(group=groupe, page=listing)
                       .values_list("permission__codename", flat=True))

        self.assertEqual(droits(redacteurs), {"add_page", "change_page"})
        self.assertIn("publish_page", droits(relecteurs))
        # Plus aucun droit sur la racine : pas de modification de l'accueil ni des pages fixes.
        self.assertFalse(GroupPagePermission.objects.filter(group__in=[redacteurs, relecteurs],
                                                            page__depth=1).exists())
        self.assertTrue(Workflow.objects.filter(name="Relecture éditoriale").exists())

    def test_ne_reecrit_pas_les_droits_ajustes(self):
        from django.contrib.auth.models import Group
        from wagtail.models import GroupPagePermission

        call_command("init_kaloum24", verbosity=0)
        redacteurs = Group.objects.get(name="Rédacteurs")
        GroupPagePermission.objects.filter(group=redacteurs, permission__codename="change_page").delete()
        call_command("init_kaloum24", verbosity=0)
        self.assertFalse(GroupPagePermission.objects.filter(group=redacteurs,
                                                            permission__codename="change_page").exists())


class ArticleRedactionTests(TestCase):
    def setUp(self):
        call_command("init_kaloum24", verbosity=0)

    def _article(self, body, **extra):
        import json

        from kaloum24_v2.news.models import ArticlePage
        from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet

        listing = NewsListingPage.objects.get()
        page = ArticlePage(
            title="Titre d'essai", slug="essai", topic=ArticleTopic.objects.first(),
            author=AuthorSnippet.objects.first(), introduction="Le chapô de l'article.",
            body=json.dumps(body), **extra,
        )
        listing.add_child(instance=page)
        page.save_revision().publish()
        return page

    def test_tous_les_blocs_de_presse_s_affichent(self):
        page = self._article(
            [
                {"type": "paragraph", "value": "<p>Premier <b>paragraphe</b>.</p>"},
                {"type": "subheading", "value": "Un intertitre"},
                {"type": "quote", "value": {"quote": "Une phrase forte", "attribution": "Le ministre"}},
                {"type": "box", "value": {"title": "À savoir", "text": "<p>Détail utile</p>"}},
                {"type": "table", "value": {"data": [["Ville", "Pluie"], ["Conakry", "40 mm"]],
                                            "first_row_is_table_header": True,
                                            "first_col_is_header": False, "table_caption": "Relevés"}},
                {"type": "section", "value": {"heading": "Ancien format",
                                              "content": [{"type": "paragraph", "value": "<p>Texte</p>"}]}},
            ],
            dateline="Conakry", sources="<p>Source : communiqué officiel</p>",
        )
        r = self.client.get(page.url)
        self.assertEqual(r.status_code, 200)
        for attendu in ("Premier", "Un intertitre", "Une phrase forte", "Le ministre", "À savoir",
                        "<table", "Conakry", "40 mm", "Ancien format", "Source : communiqué officiel",
                        "min de lecture", "news/article"):
            self.assertContains(r, attendu)

    def test_temps_de_lecture_minimum_une_minute(self):
        page = self._article([{"type": "paragraph", "value": "<p>Court.</p>"}])
        self.assertEqual(page.reading_time, 1)
        long = self._article_long()
        self.assertEqual(long.reading_time, 3)

    def _article_long(self):
        mots = " ".join(["mot"] * 600)
        from kaloum24_v2.news.models import ArticlePage
        import json
        from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet

        page = ArticlePage(title="Long", slug="long", topic=ArticleTopic.objects.first(),
                           author=AuthorSnippet.objects.first(),
                           body=json.dumps([{"type": "paragraph", "value": f"<p>{mots}</p>"}]))
        NewsListingPage.objects.get().add_child(instance=page)
        return page

    def test_recherche_dans_le_corps(self):
        from kaloum24_v2.news.models import ArticlePage

        self._article([{"type": "paragraph", "value": "<p>Zorglub est mentionné ici.</p>"}])
        # Le champ est indexé : la recherche Wagtail le trouve.
        from wagtail.search.backends import get_search_backend

        trouves = get_search_backend().search("Zorglub", ArticlePage.objects.live())
        self.assertEqual(len(list(trouves)), 1)
