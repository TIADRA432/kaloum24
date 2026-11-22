"""Recherche classée, tolérante au clavier, index alphabétique. Données factices."""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import PulaarDialect, PulaarEntry, PulaarEntryVariant, PulaarPos, PulaarSense, PulaarSource, PulaarTranslation
from .recherche import chercher
from .slug import cle_recherche


class CleTests(TestCase):
    def test_cle_recherche(self):
        self.assertEqual(cle_recherche("Ɗemngal"), "demngal")
        self.assertEqual(cle_recherche("ƴiiƴam"), "yiiyam")
        self.assertEqual(cle_recherche("  Ɓe-ɓe  "), "be be")
        self.assertEqual(cle_recherche("Ŋ"), "ng")
        self.assertEqual(cle_recherche("???"), "")


class RechercheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        cls.src = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        cls.d = PulaarDialect.objects.get(code="fuf")
        cls.nom = PulaarPos.objects.get(code="nom")
        cls.verbe = PulaarPos.objects.get(code="verbe")

        def e(lemma, sens="", pos=None, **kw):
            x = PulaarEntry.objects.create(lemma=lemma, dialect=cls.d, pos=pos or cls.nom, source=cls.src, **kw)
            if sens:
                PulaarSense.objects.create(entry=x, text=sens)
            return x

        cls.exact = e("Ɗemngal", "ɗemngal makko")
        cls.debut = e("Ɗemngalaaji")
        cls.dedans = e("Pulaar-ɗemngal")
        cls.variante_cible = e("Lawol")
        PulaarEntryVariant.objects.create(entry=cls.variante_cible, form="Ɗemɗal")
        cls.def_cible = e("Haala", "ko ɗemngal wiyetee noon")
        cls.trad = e("Koyɗol")
        PulaarTranslation.objects.create(entry=cls.trad, language_code="fra", term="langue parlée")
        cls.verbal = e("Ɓaylo", pos=cls.verbe)

    def rangs(self, q):
        return {PulaarEntry.objects.get(pk=i).lemma: r for i, r in chercher(PulaarEntry.objects.all(), q)}

    def test_classement(self):
        r = self.rangs("demngal")  # tapé sans ɗ
        self.assertEqual(r["Ɗemngal"], 1)
        self.assertEqual(r["Ɗemngalaaji"], 2)
        self.assertEqual(r["Pulaar-ɗemngal"], 3)
        self.assertEqual(r["Haala"], 5)
        ordre = [PulaarEntry.objects.get(pk=i).lemma for i, _ in chercher(PulaarEntry.objects.all(), "demngal")]
        self.assertEqual(ordre[0], "Ɗemngal")  # le mot exact vient avant tout le reste

    def test_variante_traduction_sans_doublon(self):
        self.assertEqual(self.rangs("demdal")["Lawol"], 4)
        self.assertEqual(self.rangs("langue")["Koyɗol"], 6)
        ids = [i for i, _ in chercher(PulaarEntry.objects.all(), "demngal")]
        self.assertEqual(len(ids), len(set(ids)))

    def test_saisie_courte_ne_ramene_pas_les_textes(self):
        r = self.rangs("b")
        self.assertIn("Ɓaylo", r)  # tapé b : trouve Ɓ
        self.assertNotIn("Haala", r)
        self.assertEqual(chercher(PulaarEntry.objects.all(), "!!"), [])

    def test_cle_mise_a_jour_a_la_modification(self):
        self.exact.lemma = "Ɗemngal nguuruɗe"
        self.exact.save()
        self.exact.refresh_from_db()
        self.assertEqual(self.exact.search_key, "demngal nguurude")


class PageRechercheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        src = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        d = PulaarDialect.objects.get(code="fuf")
        nom = PulaarPos.objects.get(code="nom")
        for i in range(40):
            PulaarEntry.objects.create(lemma=f"Baaba{i:02d}", dialect=d, pos=nom, source=src)
        PulaarEntry.objects.create(lemma="Ɓaawo", dialect=d, pos=nom, source=src)
        PulaarEntry.objects.create(lemma="Ceede", dialect=d, pos=nom, source=src)

    def test_resultats_pagines_avec_compteur(self):
        r = self.client.get(reverse("pulaar:accueil"), {"q": "baaba"})
        self.assertContains(r, "(40)")
        self.assertContains(r, "Page 1 sur 2")
        self.assertContains(r, 'rel="next"')
        r2 = self.client.get(reverse("pulaar:accueil"), {"q": "baaba", "page": 2})
        self.assertContains(r2, "Baaba39")

    def test_tolerance_clavier_dans_la_page(self):
        self.assertContains(self.client.get(reverse("pulaar:accueil"), {"q": "baawo"}), "Ɓaawo")

    def test_alphabet_et_filtre_lettre(self):
        r = self.client.get(reverse("pulaar:accueil"))
        self.assertContains(r, "Index alphabétique")
        for lettre in ("B", "Ɓ", "C"):
            self.assertContains(r, f">{lettre}</a>")
        r = self.client.get(reverse("pulaar:accueil"), {"lettre": "C"})
        self.assertContains(r, "Ceede")
        self.assertNotContains(r, "Baaba00")
        self.assertContains(r, "Mots en « C »")

    def test_filtre_classe_et_aucun_resultat(self):
        r = self.client.get(reverse("pulaar:accueil"), {"q": "baaba", "classe": "verbe"})
        self.assertContains(r, "Aucun résultat")

    def test_la_pagination_conserve_les_filtres(self):
        r = self.client.get(reverse("pulaar:accueil"), {"q": "baaba", "dialecte": "fuf"})
        self.assertContains(r, "q=baaba")
        self.assertContains(r, "dialecte=fuf")
