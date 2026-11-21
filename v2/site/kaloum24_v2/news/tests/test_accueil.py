import json

from django.test import TestCase
from django.utils import timezone

from kaloum24_v2.news.models import ArticlePage, Breve, NewsListingPage
from kaloum24_v2.pulaar.models import PulaarDefinition, PulaarSource, PulaarTerm, mot_du_jour
from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet


class AccueilVivantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command

        call_command("init_kaloum24", verbosity=0)

    def _article(self, titre, slug, rubrique="Société"):
        listing = NewsListingPage.objects.first()
        page = ArticlePage(title=titre, slug=slug, topic=ArticleTopic.objects.get(title=rubrique),
                           author=AuthorSnippet.objects.first(), introduction="Chapô",
                           body=json.dumps([{"type": "paragraph", "value": "<p>Texte</p>"}]))
        listing.add_child(instance=page)
        page.save_revision().publish()
        return page

    def test_accueil_vide_ne_plante_pas(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "À la une")

    def test_une_dernieres_et_rubriques(self):
        for i in range(6):
            self._article(f"Titre {i}", f"titre-{i}")
        r = self.client.get("/")
        self.assertContains(r, "À la une")
        self.assertContains(r, "Dernières nouvelles")
        self.assertContains(r, "Titre 5")  # le plus récent à la une
        self.assertContains(r, "Société")

    def test_breves_en_ligne_seulement(self):
        Breve.objects.create(texte="Brève visible", source="APA")
        Breve.objects.create(texte="Brève masquée", en_ligne=False)
        r = self.client.get("/")
        self.assertContains(r, "Flash info")
        self.assertContains(r, "Brève visible")
        self.assertNotContains(r, "Brève masquée")

    def test_mot_du_jour_donnee_reelle_et_sourcee(self):
        self.assertIsNone(mot_du_jour())
        src = PulaarSource.objects.create(name="Source test", method="import_manuel")
        t = PulaarTerm.objects.create(lemma="jam", source=src)
        PulaarDefinition.objects.create(term=t, lang="fr", text="paix")
        r = self.client.get("/")
        self.assertContains(r, "Mot du jour en Pulaar")
        self.assertContains(r, "jam")
        self.assertContains(r, "Source test")
