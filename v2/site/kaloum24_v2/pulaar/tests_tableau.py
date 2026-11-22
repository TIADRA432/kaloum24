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


class ClasseEnMasseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        src = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        cls.d = PulaarDialect.objects.get(code="fuf")
        cls.prec, cls.nom, cls.verbe = (PulaarPos.objects.get(code=c) for c in ("a-preciser", "nom", "verbe"))
        cls.e1 = PulaarEntry.objects.create(lemma="Mot1", dialect=cls.d, pos=cls.prec, source=src)
        cls.e2 = PulaarEntry.objects.create(lemma="Mot2", dialect=cls.d, pos=cls.prec, source=src)
        # collision : « Mot2 » existe déjà en classe « nom »
        PulaarEntry.objects.create(lemma="Mot2", dialect=cls.d, pos=cls.nom, source=src)
        get_user_model().objects.create_superuser("adm", "a@b.c", "x")
        get_user_model().objects.create_user("simple", "s@b.c", "x")

    def poster(self, **d):
        return self.client.post(reverse("pulaar_tableau_classe"), d, follow=True)

    def test_changement_en_masse_et_collision(self):
        self.client.login(username="adm", password="x")
        r = self.poster(ids=[self.e1.pk, self.e2.pk], pos=self.nom.pk, manque="classe", page="1")
        self.e1.refresh_from_db(); self.e2.refresh_from_db()
        self.assertEqual(self.e1.pos, self.nom)
        self.assertEqual(self.e2.pos, self.prec)  # refusée : l'entrée identique existe
        self.assertContains(r, "1 entrée(s) passée(s)")
        self.assertContains(r, "Non modifiée(s)")
        self.assertContains(r, "Mot2")

    def test_rien_de_coche_ou_classe_absente(self):
        self.client.login(username="adm", password="x")
        self.assertContains(self.poster(pos=self.nom.pk), "Coche au moins un mot")
        self.assertContains(self.poster(ids=[self.e1.pk]), "Coche au moins un mot")

    def test_reserve_a_lequipe_et_post_seulement(self):
        self.assertNotEqual(self.client.post(reverse("pulaar_tableau_classe"), {"ids": [self.e1.pk], "pos": self.nom.pk}).status_code, 200)
        self.client.login(username="simple", password="x")
        self.client.post(reverse("pulaar_tableau_classe"), {"ids": [self.e1.pk], "pos": self.nom.pk})
        self.e1.refresh_from_db()
        self.assertEqual(self.e1.pos, self.prec)
        self.client.login(username="adm", password="x")
        self.assertEqual(self.client.get(reverse("pulaar_tableau_classe")).status_code, 405)

    def test_formulaire_affiche_dans_la_file(self):
        self.client.login(username="adm", password="x")
        r = self.client.get(reverse("pulaar_tableau"), {"manque": "classe"})
        self.assertContains(r, "Appliquer aux mots cochés")
        self.assertContains(r, f'value="{self.e1.pk}"')


class FileDouteuxEtCsvTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        src = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        d, nom = PulaarDialect.objects.get(code="fuf"), PulaarPos.objects.get(code="nom")
        for lemma in ["ɓaleejo", "kala jam", "kaLa", "ƊemngaL", "Alpha"]:
            e = PulaarEntry.objects.create(lemma=lemma, dialect=d, pos=nom, source=src)
            PulaarSense.objects.create(entry=e, text="déf de " + lemma)
        get_user_model().objects.create_superuser("adm", "a@b.c", "x")
        get_user_model().objects.create_user("simple", "s@b.c", "x")

    def test_file_douteux(self):
        self.client.login(username="adm", password="x")
        r = self.client.get(reverse("pulaar_tableau"), {"manque": "douteux"})
        for bon in ["kala jam", "kaLa", "ƊemngaL"]:
            self.assertContains(r, bon)
        self.assertNotContains(r, ">ɓaleejo<")
        self.assertNotContains(r, ">Alpha<")  # majuscule initiale seule : normal

    def test_csv(self):
        self.client.login(username="adm", password="x")
        r = self.client.get(reverse("pulaar_tableau_csv"), {"manque": "douteux"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        texte = r.content.decode("utf-8-sig")
        self.assertIn("kala jam", texte)
        self.assertIn("déf de kaLa", texte)
        self.assertNotIn("Alpha", texte)

    def test_csv_reserve_et_inconnu(self):
        url = reverse("pulaar_tableau_csv")
        self.assertNotEqual(self.client.get(url, {"manque": "douteux"}).status_code, 200)
        self.client.login(username="simple", password="x")
        self.assertNotEqual(self.client.get(url, {"manque": "douteux"}).status_code, 200)
        self.client.login(username="adm", password="x")
        self.assertEqual(self.client.get(url, {"manque": "nimporte"}).status_code, 302)
