from django.core.cache import cache
from django.core.management import call_command
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from . import i18n
from .models import PulaarDomain, PulaarProposal, PulaarSource, PulaarTerm
from .slug import slugify_pulaar


class SlugTests(TestCase):
    def test_consonnes_pulaar_ne_sont_pas_supprimees(self):
        self.assertEqual(slugify_pulaar("Taskotooɗo jonnanɗe"), "taskotoodo-jonnande")
        self.assertEqual(slugify_pulaar("Ɗemngal"), "demngal")
        self.assertEqual(slugify_pulaar("ɓeydu"), "beydu")
        self.assertEqual(slugify_pulaar("ŋ"), "ng")

    def test_slug_unique_suffixe(self):
        src = PulaarSource.objects.create(name="s", method="x")
        a = PulaarTerm.objects.create(lemma="ɓeydu", source=src)
        b = PulaarTerm.objects.create(lemma="beydu", source=src)
        self.assertEqual((a.slug, b.slug), ("beydu", "beydu-2"))


class I18nTests(TestCase):
    def test_aucune_traduction_inventee(self):
        self.assertEqual(i18n.couverture(), (7, 15))
        self.assertEqual(i18n.traduire("chercher", "ff"), "Yiylo")
        # Sans équivalent attesté : repli sur le français, jamais une invention.
        self.assertEqual(i18n.traduire("dictionnaire", "ff"), "Dictionnaire")
        self.assertEqual(i18n.traduire("inconnue", "ff"), "inconnue")


class SeedEtVuesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)

    def test_seed_idempotent(self):
        n = PulaarTerm.objects.count()
        self.assertEqual(n, 22)
        call_command("seed_pulaar", verbosity=0)
        self.assertEqual(PulaarTerm.objects.count(), n)

    def test_provenance_obligatoire_et_protegee(self):
        src = PulaarSource.objects.get(method="wiktionary")
        with self.assertRaises(ProtectedError):
            src.delete()

    def test_accueil_liste_sans_recherche(self):
        r = self.client.get(reverse("pulaar:accueil"))
        self.assertContains(r, "aada")
        self.assertContains(r, "22 terme")
        self.assertContains(r, "0 terme")  # couverture monolingue honnête

    def test_recherche_tolerante_au_clavier(self):
        src = PulaarSource.objects.get(method="wiktionary")
        t = PulaarTerm.objects.create(lemma="Taskotooɗo jonnanɗe", source=src)
        r = self.client.get(reverse("pulaar:accueil"), {"q": "taskotoodo"})
        self.assertContains(r, t.lemma)

    def test_recherche_dans_la_definition(self):
        r = self.client.get(reverse("pulaar:accueil"), {"q": "coutume"})
        self.assertContains(r, "aada")

    def test_page_terme_et_404(self):
        t = PulaarTerm.objects.get(lemma="aada")
        r = self.client.get(reverse("pulaar:terme", args=[t.slug]))
        self.assertContains(r, "Wiktionary")
        self.assertContains(r, "pas encore vérifié")
        self.assertEqual(self.client.get(reverse("pulaar:terme", args=["nope"])).status_code, 404)

    def test_interface_pulaar_partielle_affichee(self):
        r = self.client.get(reverse("pulaar:accueil"), {"lang": "ff"})
        self.assertContains(r, "Yiylo")
        self.assertContains(r, "7/15")
        self.assertNotContains(self.client.get(reverse("pulaar:accueil")), "7/15")

    def test_domaine(self):
        d = PulaarDomain.objects.create(name="Agriculture")
        r = self.client.get(reverse("pulaar:domaine", args=[d.slug]))
        self.assertContains(r, "Aucun terme")


class PropositionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("pulaar:proposer")

    def test_formulaire_affiche(self):
        self.assertContains(self.client.get(self.url), "csrfmiddlewaretoken")

    def test_definition_requise(self):
        r = self.client.post(self.url, {"term_lemma": "x", "definition_fr": "ab"})
        self.assertContains(r, "au moins une définition")
        self.assertEqual(PulaarProposal.objects.count(), 0)

    def test_pulaar_seul_suffit_et_reste_en_attente(self):
        r = self.client.post(self.url, {"term_lemma": "hoore", "definition_ff": "Cifol cuuɗi ɗuuɗi"})
        self.assertRedirects(r, reverse("pulaar:accueil"))
        p = PulaarProposal.objects.get()
        self.assertEqual(p.status, "en_attente")
        self.assertEqual(PulaarTerm.objects.count(), 0)  # jamais publié directement

    def test_robot_ignore(self):
        self.client.post(self.url, {"term_lemma": "spam", "definition_fr": "spam spam", "site_web": "http://x"})
        self.assertEqual(PulaarProposal.objects.count(), 0)

    def test_limite_par_ip(self):
        for i in range(7):
            self.client.post(self.url, {"term_lemma": f"m{i}", "definition_fr": "définition ok"})
        self.assertEqual(PulaarProposal.objects.count(), 5)

    def test_validation_publie_le_terme_une_seule_fois(self):
        p = PulaarProposal.objects.create(term_lemma="hoore", definition_ff="Cifol cuuɗi", definition_fr="la tête")
        p.status = "valide"
        p.save()
        t = PulaarTerm.objects.get(lemma="hoore")
        self.assertEqual(t.status, "documented")  # jamais présumé « validé »
        self.assertEqual(t.source.method, "communaute")
        self.assertEqual(t.definitions.count(), 2)
        p.save()  # re-sauvegarde : pas de doublon
        self.assertEqual(t.definitions.count(), 2)
        self.assertEqual(PulaarTerm.objects.count(), 1)

    def test_rejet_ne_publie_rien(self):
        p = PulaarProposal.objects.create(term_lemma="x", definition_fr="def ok", status="rejete")
        self.assertEqual(PulaarTerm.objects.count(), 0)
        self.assertIsNone(p.published_term)
