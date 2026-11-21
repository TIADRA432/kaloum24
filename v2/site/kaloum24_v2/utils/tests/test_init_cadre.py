from django.core.management import call_command
from django.test import TestCase

from kaloum24_v2.standardpages.models import StandardPage
from kaloum24_v2.utils.models import ArticleTopic


class InitCadreTests(TestCase):
    def setUp(self):
        call_command("init_kaloum24", verbosity=0)

    def test_rubriques_definitives(self):
        for titre in ("Politique", "Faits divers", "Régions", "Mines & Énergie", "Opinions & Tribunes", "Pulaar"):
            self.assertTrue(ArticleTopic.objects.filter(title=titre).exists(), titre)

    def test_pages_cadre_en_brouillon(self):
        slugs = {"charte-editoriale", "mentions-legales", "a-propos"}
        pages = StandardPage.objects.filter(slug__in=slugs)
        self.assertEqual({p.slug for p in pages}, slugs)
        self.assertFalse(any(p.live for p in pages))

    def test_aucun_fait_invente(self):
        page = StandardPage.objects.get(slug="mentions-legales")
        self.assertIn("À COMPLÉTER", json_text(page))

    def test_idempotent_et_respecte_les_modifications(self):
        page = StandardPage.objects.get(slug="a-propos")
        page.introduction = "Texte édité par l'équipe"
        page.save()
        call_command("init_kaloum24", verbosity=0)
        self.assertEqual(StandardPage.objects.filter(slug="a-propos").count(), 1)
        self.assertEqual(StandardPage.objects.get(slug="a-propos").introduction, "Texte édité par l'équipe")
        self.assertEqual(ArticleTopic.objects.filter(title="Régions").count(), 1)


def json_text(page):
    return str(page.body.raw_data)
