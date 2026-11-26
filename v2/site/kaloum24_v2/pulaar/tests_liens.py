"""Hypertextualisation des définitions."""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from . import liens
from .models import PulaarDialect, PulaarEntry, PulaarMutation, PulaarPos, PulaarSense, PulaarSource, PulaarStopword


def cree(lemma, definition="", source=None, d="fuf", pos="nom", homonyme=1, statut="documented"):
    e = PulaarEntry.objects.create(lemma=lemma, dialect=PulaarDialect.objects.get(code=d), pos=PulaarPos.objects.get(code=pos),
                                   source=source, homonym_index=homonyme, status=statut)
    if definition:
        PulaarSense.objects.create(entry=e, text=definition)
    return e


class LiensBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        cls.libre = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        cls.prive = PulaarSource.objects.create(name="Privée", rights_status="to_check")

    def html(self, entree):
        s = entree.senses.first()
        s.refresh_from_db()
        return s.text_html

    def relier(self):
        liens.relier_sens(tous=True)


class TokenisationTests(LiensBase):
    def test_ponctuation_espaces_et_lettres_speciales_conserves(self):
        cible = cree("ɗemngal", source=self.libre)
        e = cree("alpha", "Ko ɗemngal,  « ɗemngal »; (ɓe) <b>x</b> & fin.", source=self.libre)
        self.relier()
        h = self.html(e)
        self.assertIn(f'>ɗemngal</a>,  « ɗemngal »; (ɓe) &lt;b&gt;x&lt;/b&gt; &amp; fin.', h)  # un seul lien, reste intact
        self.assertEqual(h.count("<a "), 1)
        self.assertIn(f'data-entry-id="{cible.id}"', h)
        self.assertIn(f'href="{reverse("pulaar:terme", args=[cible.slug])}"', h)

    def test_adlam_et_marques_combinantes(self):
        cible = cree("𞤢𞤣𞤢𞤥𞤢", source=self.libre)
        e = cree("alpha", "ko 𞤢𞤣𞤢𞤥𞤢 jam", source=self.libre)
        self.relier()
        self.assertIn(f'data-entry-id="{cible.id}"', self.html(e))

    def test_casse_ignoree_et_forme_variante(self):
        cible = cree("Neɗɗo", source=self.libre)
        cible.variants.create(form="Nedɗo")
        cible.save()
        e = cree("alpha", "NEƊƊO e nedɗo", source=self.libre)
        self.relier()
        h = self.html(e)
        self.assertEqual(h.count("<a "), 1)  # un lien par cible et par définition
        self.assertIn("NEƊƊO</a>", h)

    def test_lettres_speciales_distinctes_par_defaut(self):
        cree("be", source=self.libre)
        e = cree("alpha", "ɓe kuuɓal", source=self.libre)
        self.relier()
        self.assertNotIn("<a ", self.html(e))  # « ɓe » n'est pas « be »


class RegleTests(LiensBase):
    def test_pas_d_auto_lien(self):
        e = cree("ndiyam", "ndiyam e ndiyam", source=self.libre)
        e.variants.create(form="ndiyaam")
        e.save()
        self.relier()
        self.assertNotIn("<a ", self.html(e))
        e2 = cree("gamma", "ndiyaam", source=self.libre)
        self.relier()
        self.assertIn("<a ", self.html(e2))

    def test_mots_courts_et_absents_restent_en_texte(self):
        cree("ko", source=self.libre)
        e = cree("alpha", "ko inconnu", source=self.libre)
        self.relier()
        self.assertEqual(self.html(e), "ko inconnu")

    def test_mot_sans_lien_manuel_et_force(self):
        cree("huunde", source=self.libre)
        cree("ko", source=self.libre)
        e = cree("alpha", "huunde ko", source=self.libre)
        PulaarStopword.objects.create(forme="Huunde", mode="exclude", origine="manual")
        PulaarStopword.objects.create(forme="ko", mode="link", origine="manual")
        self.relier()
        h = self.html(e)
        self.assertNotIn(">huunde</a>", h)
        self.assertIn(">ko</a>", h)  # forcé malgré sa longueur

    def test_seuil_de_frequence_automatique(self):
        cree("neɗɗo", source=self.libre)
        for i in range(4):
            cree(f"mot{i}x", "neɗɗo", source=self.libre)
        e = cree("rare", "neɗɗo", source=self.libre)
        liens.recalculer_tout(seuil=3)
        self.assertTrue(PulaarStopword.objects.filter(cle="neɗɗo", origine="auto").exists())
        self.assertNotIn("<a ", self.html(e))
        # une règle manuelle « lier » l'emporte sur l'automatique
        PulaarStopword.objects.create(forme="neɗɗo", mode="link", origine="manual")
        liens.recalculer_tout(seuil=3)
        self.assertFalse(PulaarStopword.objects.filter(cle="neɗɗo", origine="auto").exists())
        self.assertIn("<a ", self.html(e))

    def test_homonymes(self):
        a = cree("laabi", source=self.libre, homonyme=2, pos="nom")
        b = cree("laabi", source=self.libre, homonyme=1, pos="verbe")
        e = cree("alpha", "laabi", source=self.libre)
        self.relier()
        h = self.html(e)
        self.assertIn(f'data-entry-id="{b.id}"', h)  # le n° 1 est le lien principal
        self.assertIn('data-homonyms="2"', h)
        self.assertIn(a.slug, h)  # l'autre est proposée dans data-alternatives

    def test_composes_avec_trait_d_union(self):
        cible = cree("lekki", source=self.libre)
        e = cree("alpha", "lekki-lekki", source=self.libre)
        self.relier()
        self.assertEqual(self.html(e).count("<a "), 1)
        self.assertTrue(self.html(e).startswith("<a "))


class VisibiliteTests(LiensBase):
    def test_definition_publique_ne_pointe_que_vers_du_public(self):
        public = cree("mawɗo", source=self.libre)
        cache = cree("nayeejo", source=self.prive)
        e = cree("alpha", "mawɗo nayeejo", source=self.libre)
        self.relier()
        h = self.html(e)
        self.assertIn(f'data-entry-id="{public.id}"', h)
        self.assertNotIn(f'data-entry-id="{cache.id}"', h)
        self.assertNotIn(f"terme/{cache.slug}/", h)

    def test_definition_non_publique_peut_pointer_partout_sauf_brouillon(self):
        cache = cree("nayeejo", source=self.prive)
        brouillon = cree("bruyon", source=self.libre, statut="draft")
        e = cree("alpha", "nayeejo bruyon", source=self.prive)
        self.relier()
        h = self.html(e)
        self.assertIn(f'data-entry-id="{cache.id}"', h)
        self.assertNotIn(f'data-entry-id="{brouillon.id}"', h)

    def test_changement_de_droits_recalcule(self):
        cache = cree("nayeejo", source=self.prive)
        e = cree("alpha", "nayeejo", source=self.libre)
        with self.captureOnCommitCallbacks(execute=True):
            self.relier()
        self.assertNotIn("<a ", self.html(e))
        with self.captureOnCommitCallbacks(execute=True):
            self.prive.rights_status = "permission_granted"
            self.prive.save()
        self.assertIn(f'data-entry-id="{cache.id}"', self.html(e))

    def test_page_publique_sans_lien_vers_non_public(self):
        cache = cree("nayeejo", "ko", source=self.prive)
        e = cree("alpha", "nayeejo", source=self.libre)
        self.relier()
        r = self.client.get(reverse("pulaar:terme", args=[e.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, f"terme/{cache.slug}/")
        self.assertNotContains(r, "<a href=\"/pulaar/terme/nayeejo")
        self.assertEqual(self.client.get(reverse("pulaar:terme", args=[cache.slug])).status_code, 404)


class SignauxTests(LiensBase):
    def test_nouveau_mot_relie_les_anciennes_definitions(self):
        e = cree("alpha", "ko nayeejo", source=self.libre)
        with self.captureOnCommitCallbacks(execute=True):
            self.relier()
        self.assertNotIn("<a ", self.html(e))
        with self.captureOnCommitCallbacks(execute=True):
            cible = cree("nayeejo", source=self.libre)
        self.assertIn(f'data-entry-id="{cible.id}"', self.html(e))

    def test_suppression_retire_le_lien(self):
        cible = cree("nayeejo", source=self.libre)
        e = cree("alpha", "nayeejo", source=self.libre)
        with self.captureOnCommitCallbacks(execute=True):
            self.relier()
        self.assertIn("<a ", self.html(e))
        with self.captureOnCommitCallbacks(execute=True):
            cible.delete()
        self.assertNotIn("<a ", self.html(e))

    def test_modifier_une_definition_la_recalcule(self):
        cible = cree("nayeejo", source=self.libre)
        e = cree("alpha", "ko", source=self.libre)
        s = e.senses.first()
        with self.captureOnCommitCallbacks(execute=True):
            s.text = "nayeejo e ko"
            s.save()
        self.assertIn(f'data-entry-id="{cible.id}"', self.html(e))

    def test_texte_brut_tant_que_non_calcule(self):
        e = cree("alpha", "a < b", source=self.libre)
        r = self.client.get(reverse("pulaar:terme", args=[e.slug]))
        self.assertContains(r, "a &lt; b")


class MutationsEtCommandeTests(LiensBase):
    def test_mutation_inactive_par_defaut_puis_activee(self):
        cible = cree("gorko", source=self.libre)
        e = cree("alpha", "worko", source=self.libre)
        self.relier()
        self.assertNotIn("<a ", self.html(e))
        PulaarMutation.objects.create(initiale_a="g", initiale_b="w", actif=True)
        self.relier()
        h = self.html(e)
        self.assertIn(f'data-entry-id="{cible.id}"', h)
        self.assertIn('data-match="mutation"', h)

    def test_rapport_ne_change_rien(self):
        cree("gorko", source=self.libre)
        cree("alpha", "worko worko", source=self.libre)
        r = liens.rapport_mutations([("g", "w")])
        self.assertEqual(r[0]["mots"], 1)
        self.assertEqual(r[0]["occurrences"], 2)
        self.assertEqual(PulaarMutation.objects.count(), 0)

    def test_commande_en_retard_puis_idempotente(self):
        cree("nayeejo", source=self.libre)
        e = cree("alpha", "nayeejo", source=self.libre)
        call_command("hypertextualiser", verbosity=0)
        self.assertIn("<a ", self.html(e))
        n, _ = liens.relier_en_retard()
        self.assertEqual(n, 0)  # rien à refaire
        call_command("hypertextualiser", "--tout", verbosity=0)
        self.assertIn("<a ", self.html(e))

    def test_bouton_du_tableau_de_bord(self):
        cree("nayeejo", source=self.libre)
        e = cree("alpha", "nayeejo", source=self.libre)
        get_user_model().objects.create_superuser("adm", "a@b.c", "x")
        get_user_model().objects.create_user("simple", "s@b.c", "x")
        url = reverse("pulaar_tableau_liens")
        self.assertEqual(self.client.post(url).status_code, 302)  # anonyme : renvoyé vers la connexion
        self.assertNotIn("<a ", self.html(e))
        self.client.login(username="simple", password="x")
        self.assertNotEqual(self.client.post(url).status_code, 200)
        self.assertNotIn("<a ", self.html(e))
        self.client.login(username="adm", password="x")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertIn("<a ", self.html(e))
        self.assertContains(self.client.get(reverse("pulaar_tableau")), "Recalculer tous les liens")


class PremierPassageTests(LiensBase):
    def test_premier_passage_calcule_les_mots_outils(self):
        cree("neɗɗo", source=self.libre)
        for i in range(3):
            cree(f"mot{i}x", "neɗɗo", source=self.libre)
        with self.settings(LIENS_FREQUENCE_MAX=3):
            call_command("hypertextualiser", verbosity=0)
        self.assertTrue(PulaarStopword.objects.filter(cle="neɗɗo", origine="auto").exists())
        self.assertNotIn("<a ", self.html(PulaarEntry.objects.get(lemma="mot0x")))
