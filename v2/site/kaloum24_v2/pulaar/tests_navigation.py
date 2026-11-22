"""Retour aux résultats, mots voisins, recherche depuis la fiche."""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import PulaarDialect, PulaarEntry, PulaarPos, PulaarSource


class NavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        src = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        d, nom = PulaarDialect.objects.get(code="fuf"), PulaarPos.objects.get(code="nom")
        cls.e = {m: PulaarEntry.objects.create(lemma=m, dialect=d, pos=nom, source=src)
                 for m in ("Zaaka", "Zeema", "Ziima")}

    def url(self, mot, **p):
        return reverse("pulaar:terme", args=[self.e[mot].slug]), p

    def test_les_cartes_gardent_le_contexte(self):
        r = self.client.get(reverse("pulaar:accueil"), {"q": "ze", "dialecte": "fuf"})
        self.assertContains(r, "?depuis=q%3Dze%26dialecte%3Dfuf")

    def test_retour_aux_resultats(self):
        u, _ = self.url("Zeema")
        r = self.client.get(u, {"depuis": "q=ze&dialecte=fuf&page=2"})
        self.assertContains(r, "Retour aux résultats")
        self.assertContains(r, "?q=ze&amp;dialecte=fuf&amp;page=2")

    def test_sans_contexte_retour_au_dictionnaire(self):
        self.assertContains(self.client.get(self.url("Zeema")[0]), "Retour au dictionnaire")

    def test_parametres_inconnus_ou_dangereux_ignores(self):
        r = self.client.get(self.url("Zeema")[0], {"depuis": "q=ze&evil=1&next=http://x.com&lang=fr"})
        self.assertContains(r, "?q=ze&amp;lang=fr")
        self.assertNotContains(r, "evil")
        self.assertNotContains(r, "x.com")

    def test_voisins_alphabetiques(self):
        r = self.client.get(self.url("Zeema")[0])
        self.assertContains(r, "← Zaaka")
        self.assertContains(r, "Ziima →")
        self.assertContains(r, 'rel="prev"')
        premier = self.client.get(self.url("Zaaka")[0])
        self.assertNotContains(premier, 'rel="prev"')
        self.assertContains(premier, "Zeema →")

    def test_voisins_ne_revelent_pas_les_entrees_non_publiques(self):
        PulaarEntry.objects.create(lemma="Zeemb", dialect=self.e["Zeema"].dialect, pos=self.e["Zeema"].pos,
                                   source=PulaarSource.objects.create(name="Privé", rights_status="to_check"))
        r = self.client.get(self.url("Zeema")[0])
        self.assertNotContains(r, "Zeemb")

    def test_recherche_depuis_la_fiche(self):
        r = self.client.get(self.url("Zeema")[0])
        self.assertContains(r, 'name="q"')
        self.assertContains(r, "Chercher un autre mot")


class AvertissementDroitsTests(TestCase):
    def test_message_quand_une_source_devient_publique(self):
        from django.contrib.auth import get_user_model
        call_command("seed_pulaar", verbosity=0)
        src = PulaarSource.objects.create(name="Livre", rights_status="to_check")
        d, nom = PulaarDialect.objects.get(code="fuf"), PulaarPos.objects.get(code="nom")
        PulaarEntry.objects.create(lemma="Zzz", dialect=d, pos=nom, source=src)
        get_user_model().objects.create_superuser("adm", "a@b.c", "x")
        self.client.login(username="adm", password="x")
        url = f"/admin/snippets/pulaar/pulaarsource/edit/{src.pk}/"
        base = {"name": "Livre", "url": "", "license": "", "method": "import", "rights_note": "x"}
        r = self.client.post(url, {**base, "rights_status": "public_domain"}, follow=True)
        self.assertContains(r, "visibles de tout le monde")
        r = self.client.post(url, {**base, "rights_status": "to_check"}, follow=True)
        self.assertContains(r, "ne sont pas visibles du public")


class PolicePulaarTests(TestCase):
    def test_police_pulaar_declaree_et_presente(self):
        import os
        from django.contrib.staticfiles import finders
        css = open(finders.find("pulaar/css/pulaar.css"), encoding="utf-8").read()
        self.assertIn("'Charis Pulaar'", css)
        self.assertIn("U+0253", css)  # ɓ
        self.assertIn("U+0257", css)  # ɗ
        self.assertIn("U+014A-014B", css)  # Ŋ ŋ
        self.assertIn("U+01B3-01B4", css)  # Ƴ ƴ
        for f in ("charis-400", "charis-700", "charis-ext-400", "charis-ext-700"):
            self.assertTrue(os.path.exists(finders.find(f"pulaar/fonts/charis/{f}.woff2")), f)

    def test_le_mot_est_balise_en_pulaar(self):
        call_command("seed_pulaar", verbosity=0)
        e = PulaarEntry.objects.filter(source__rights_status="open_license").first()
        r = self.client.get(reverse("pulaar:terme", args=[e.slug]))
        self.assertContains(r, '<h1 lang="ff">')


class DecorTests(TestCase):
    def test_decor_present_et_decoratif(self):
        from django.contrib.staticfiles import finders
        r = self.client.get(reverse("pulaar:accueil"))
        for nom in ("anneaux-or", "leppi", "vache-or", "calebasse-bordeaux", "gourde-bordeaux"):
            self.assertContains(r, nom)
        self.assertContains(r, 'class="tc-pied" aria-hidden="true"')
        for f in ("leppi-h", "leppi-v", "anneaux-or", "vannerie-or", "vache-or", "calebasse-bordeaux", "gourde-bordeaux"):
            self.assertIsNotNone(finders.find(f"pulaar/img/decor/{f}.svg"), f)
        css = open(finders.find("pulaar/css/pulaar.css"), encoding="utf-8").read()
        self.assertIn("prefers-reduced-motion", css)
