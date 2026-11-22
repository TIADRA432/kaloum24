"""Tableau de bord du dictionnaire (administration)."""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import PulaarDialect, PulaarEntry, PulaarPos, PulaarPronunciation, PulaarSense, PulaarSource


class TableauTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        src = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        d, nom = PulaarDialect.objects.get(code="fuf"), PulaarPos.objects.get(code="nom")
        cls.a = PulaarEntry.objects.create(lemma="Alpha", dialect=d, pos=nom, source=src)
        PulaarSense.objects.create(entry=cls.a, text="def")
        PulaarPronunciation.objects.create(entry=cls.a, ipa="[al.fa]")
        cls.b = PulaarEntry.objects.create(lemma="Beta", dialect=d, pos=nom, source=src, status="validated" if False else "documented")
        get_user_model().objects.create_superuser("adm", "a@b.c", "x")
        get_user_model().objects.create_user("simple", "s@b.c", "x")

    def test_reserve_a_lequipe(self):
        url = reverse("pulaar_tableau")
        self.assertNotEqual(self.client.get(url).status_code, 200)
        self.client.login(username="simple", password="x")
        self.assertNotEqual(self.client.get(url).status_code, 200)

    def test_chiffres_et_files(self):
        self.client.login(username="adm", password="x")
        r = self.client.get(reverse("pulaar_tableau"))
        self.assertContains(r, "Où en est le dictionnaire")
        self.assertContains(r, "avec une prononciation (API)")
        r = self.client.get(reverse("pulaar_tableau"), {"manque": "ipa"})
        self.assertContains(r, "Beta")
        self.assertNotContains(r, ">Alpha<")  # Alpha a une prononciation
        self.assertContains(r, f"/admin/snippets/pulaar/pulaarentry/edit/{self.b.pk}/")

    def test_filtre_inconnu_ignore(self):
        self.client.login(username="adm", password="x")
        self.assertEqual(self.client.get(reverse("pulaar_tableau"), {"manque": "nimporte"}).status_code, 200)
