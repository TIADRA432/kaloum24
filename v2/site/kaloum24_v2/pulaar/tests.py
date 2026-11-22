from django.core.cache import cache
from django.core.management import call_command
from io import StringIO

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from . import i18n
from django.core.exceptions import ValidationError

from .models import (
    PulaarDialect, PulaarDomain, PulaarEntry, PulaarExternalDictionary, PulaarPos, PulaarProposal,
    PulaarSense, PulaarSource, PulaarTranslation, mot_du_jour,
)
from .management.commands.verifier_dictionnaire import verifier
from .slug import slugify_pulaar


class SlugTests(TestCase):
    def test_consonnes_pulaar_ne_sont_pas_supprimees(self):
        self.assertEqual(slugify_pulaar("Taskotooɗo jonnanɗe"), "taskotoodo-jonnande")
        self.assertEqual(slugify_pulaar("Ɗemngal"), "demngal")
        self.assertEqual(slugify_pulaar("ɓeydu"), "beydu")
        self.assertEqual(slugify_pulaar("ŋ"), "ng")

    def test_slug_unique_suffixe(self):
        call_command("seed_pulaar", verbosity=0)
        src = PulaarSource.objects.create(name="s", method="x")
        d, p = PulaarDialect.objects.get(code="fuf"), PulaarPos.objects.get(code="nom")
        a = PulaarEntry.objects.create(lemma="ɓeydu", source=src, dialect=d, pos=p)
        b = PulaarEntry.objects.create(lemma="beydu", source=src, dialect=d, pos=p)
        self.assertEqual((a.slug, b.slug), ("beydu", "beydu-2"))


class I18nTests(TestCase):
    def test_aucune_traduction_inventee(self):
        self.assertEqual(i18n.couverture(), (7, 15))
        self.assertEqual(i18n.traduire("chercher", "ff"), "Yiylo")
        # Sans équivalent attesté : repli sur le français, jamais une invention.
        self.assertEqual(i18n.traduire("dictionnaire", "ff"), "Dictionnaire")
        self.assertEqual(i18n.traduire("inconnue", "ff"), "inconnue")


class DictionnaireBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        cls.fuf = PulaarDialect.objects.get(code="fuf")
        cls.nom = PulaarPos.objects.get(code="nom")
        cls.libre = PulaarSource.objects.get(method="wiktionary")

    def entree(self, lemma="hoore", source=None, **kw):
        return PulaarEntry.objects.create(lemma=lemma, dialect=self.fuf, pos=self.nom,
                                          source=source or self.libre, **kw)


class SeedEtVuesTests(DictionnaireBase):
    def test_seed_idempotent_et_reference(self):
        n = PulaarEntry.objects.count()
        self.assertEqual(n, 22)
        call_command("seed_pulaar", verbosity=0)
        self.assertEqual(PulaarEntry.objects.count(), n)
        self.assertEqual(PulaarDialect.objects.count(), 10)
        self.assertEqual(set(PulaarDialect.objects.values_list("code", flat=True)),
                         {"ful", "fuf", "fuc", "ffm", "fue", "fuh", "fuq", "fuv", "fub", "fui"})
        # aucun nom pulaar de classe grammaticale inventé
        self.assertFalse(PulaarPos.objects.exclude(name_ff="").exists())

    def test_gloses_wiktionary_sont_des_traductions_pas_des_definitions(self):
        e = PulaarEntry.objects.get(lemma="aada")
        self.assertEqual(e.senses.count(), 0)
        self.assertEqual(set(e.translations.values_list("language_code", flat=True)), {"fra", "eng"})

    def test_provenance_obligatoire_et_protegee(self):
        with self.assertRaises(ProtectedError):
            self.libre.delete()

    def test_accueil_liste_sans_recherche(self):
        r = self.client.get(reverse("pulaar:accueil"))
        self.assertContains(r, "aada")
        self.assertContains(r, "22 terme")
        self.assertContains(r, "0 terme")  # couverture monolingue honnête
        self.assertContains(r, "Définition en pulaar à venir")

    def test_recherche_tolerante_au_clavier(self):
        t = self.entree("Taskotooɗo jonnanɗe")
        r = self.client.get(reverse("pulaar:accueil"), {"q": "taskotoodo"})
        self.assertContains(r, t.lemma)

    def test_recherche_dans_les_traductions(self):
        r = self.client.get(reverse("pulaar:accueil"), {"q": "coutume"})
        self.assertContains(r, "aada")

    def test_filtre_par_dialecte(self):
        self.entree("hoore")
        r = self.client.get(reverse("pulaar:accueil"), {"dialecte": "fuf"})
        self.assertContains(r, "hoore")
        self.assertNotContains(r, "aada")  # aada est rattaché à « ful »

    def test_page_terme_et_404(self):
        t = PulaarEntry.objects.get(lemma="aada")
        r = self.client.get(reverse("pulaar:terme", args=[t.slug]))
        self.assertContains(r, "Wiktionary")
        self.assertContains(r, "pas encore vérifié")
        self.assertContains(r, "Traductions")
        self.assertContains(r, "pas encore de définition en pulaar")
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


class DroitsEtStatutTests(DictionnaireBase):
    def test_source_a_verifier_par_defaut_et_cachee_du_public(self):
        src = PulaarSource.objects.create(name="Livre", method="import_manuel")
        self.assertEqual(src.rights_status, "to_check")
        e = self.entree("secret", source=src)
        self.assertEqual(self.client.get(reverse("pulaar:terme", args=[e.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("pulaar:accueil")), "secret")
        src.rights_status = PulaarSource.ACCORD
        src.save()
        self.assertEqual(self.client.get(reverse("pulaar:terme", args=[e.slug])).status_code, 200)

    def test_brouillon_non_public(self):
        e = self.entree("brouillon", status=PulaarEntry.BROUILLON)
        self.assertEqual(self.client.get(reverse("pulaar:terme", args=[e.slug])).status_code, 404)

    def test_valide_exige_une_definition_pulaar(self):
        e = self.entree("hoore")
        e.status = PulaarEntry.VALIDE
        with self.assertRaises(ValidationError):
            e.save()
        PulaarSense.objects.create(entry=e, text="Cifol cuuɗi ɗuuɗi")
        e = PulaarEntry.objects.get(pk=e.pk)
        e.status = PulaarEntry.VALIDE
        e.save()  # accepté : il y a un sens
        self.assertEqual(PulaarEntry.objects.get(pk=e.pk).status, "validated")

    def test_homonymes_distincts_mais_pas_de_doublon(self):
        self.entree("laawol")
        self.entree("laawol", homonym_index=2)
        with self.assertRaises(IntegrityError):
            self.entree("laawol", homonym_index=2)

    def test_mot_du_jour_exige_un_sens_en_pulaar(self):
        self.assertIsNone(mot_du_jour())  # les 22 entrées Wiktionary n'ont pas de sens
        e = self.entree("jam")
        PulaarSense.objects.create(entry=e, text="Fëw e laaw")
        m = mot_du_jour()
        self.assertEqual(m["terme"], e)
        self.assertEqual(m["definition"].text, "Fëw e laaw")


class TraductionsEtLiensTests(DictionnaireBase):
    def test_lien_construit_a_laffichage_avec_mot_encode(self):
        e = self.entree("hoore")
        d = PulaarExternalDictionary.objects.get(code="wiktionnaire-fr")
        tr = PulaarTranslation.objects.create(entry=e, language_code="fra", term="tête d'âne",
                                              external_dictionary=d, source=self.libre)
        self.assertEqual(tr.lien, "https://fr.wiktionary.org/wiki/t%C3%AAte_d%27%C3%A2ne")
        r = self.client.get(reverse("pulaar:terme", args=[e.slug]))
        self.assertContains(r, 'href="https://fr.wiktionary.org/wiki/t%C3%AAte_d%27%C3%A2ne"')
        self.assertContains(r, "noopener noreferrer nofollow")

    def test_sans_dictionnaire_externe_pas_de_lien(self):
        e = self.entree("hoore")
        tr = PulaarTranslation.objects.create(entry=e, language_code="fra", term="tête")
        self.assertIsNone(tr.lien)

    def test_domaines_non_autorises_refuses(self):
        for modele in ("http://fr.wiktionary.org/wiki/{term}",  # pas https
                       "https://exemple.com/{term}",             # domaine non autorisé
                       "https://evilwiktionary.org/{term}",      # faux sous-domaine
                       "https://fr.wiktionary.org/wiki/mot"):    # sans {term}
            d = PulaarExternalDictionary(code="x", name="x", language_code="fra", url_template=modele)
            with self.assertRaises(ValidationError, msg=modele):
                d.clean()
            self.assertIsNone(d.url_for("mot"), modele)

    def test_traduction_unique_par_entree_langue_mot(self):
        e = self.entree("hoore")
        PulaarTranslation.objects.create(entry=e, language_code="fra", term="tête")
        with self.assertRaises(IntegrityError):
            PulaarTranslation.objects.create(entry=e, language_code="fra", term="tête")

    def test_code_langue_iso3(self):
        e = self.entree("hoore")
        tr = PulaarTranslation(entry=e, language_code="fr", term="tête")
        with self.assertRaises(ValidationError):
            tr.full_clean(exclude=["external_dictionary", "source"])


class VerifierDictionnaireTests(DictionnaireBase):
    def test_conforme_apres_seed(self):
        violations, infos = verifier()
        self.assertEqual(violations, [])
        self.assertTrue(any("sans définition en pulaar" in m for m in infos))
        call_command("verifier_dictionnaire", stdout=StringIO())

    def test_detecte_une_entree_validee_sans_sens(self):
        e = self.entree("hoore")
        PulaarEntry.objects.filter(pk=e.pk).update(status="validated")  # contourne save()
        violations, _ = verifier()
        self.assertTrue(any("validée sans définition" in m for m in violations))
        with self.assertRaises(SystemExit):
            call_command("verifier_dictionnaire", stdout=StringIO(), stderr=StringIO())


class PropositionTests(DictionnaireBase):
    def setUp(self):
        cache.clear()
        self.url = reverse("pulaar:proposer")

    def test_formulaire_affiche(self):
        self.assertContains(self.client.get(self.url), "csrfmiddlewaretoken")

    def test_definition_pulaar_requise(self):
        r = self.client.post(self.url, {"term_lemma": "x", "translation_fr": "la tête"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PulaarProposal.objects.count(), 0)

    def test_pulaar_seul_suffit_et_reste_en_attente(self):
        n = PulaarEntry.objects.count()
        r = self.client.post(self.url, {"term_lemma": "hoore", "definition_ff": "Cifol cuuɗi ɗuuɗi"})
        self.assertRedirects(r, reverse("pulaar:accueil"))
        p = PulaarProposal.objects.get()
        self.assertEqual(p.status, "en_attente")
        self.assertEqual(PulaarEntry.objects.count(), n)  # jamais publié directement

    def test_robot_ignore(self):
        self.client.post(self.url, {"term_lemma": "spam", "definition_ff": "spam spam", "site_web": "http://x"})
        self.assertEqual(PulaarProposal.objects.count(), 0)

    def test_limite_par_ip(self):
        for i in range(7):
            self.client.post(self.url, {"term_lemma": f"m{i}", "definition_ff": "définition ok"})
        self.assertEqual(PulaarProposal.objects.count(), 5)

    def test_validation_publie_une_seule_fois_et_la_traduction_reste_une_traduction(self):
        n = PulaarEntry.objects.count()
        p = PulaarProposal.objects.create(term_lemma="hoore", definition_ff="Cifol cuuɗi", translation_fr="la tête")
        p.status = "valide"
        p.save()
        e = PulaarEntry.objects.get(lemma="hoore")
        self.assertEqual(e.status, "documented")  # jamais présumé « validé »
        self.assertEqual(e.source.method, "communaute")
        self.assertTrue(e.source.is_publishable)
        self.assertEqual([s.text for s in e.senses.all()], ["Cifol cuuɗi"])  # pulaar seulement
        self.assertEqual([t.term for t in e.translations.filter(language_code="fra")], ["la tête"])
        p.save()  # re-sauvegarde : pas de doublon
        self.assertEqual(e.senses.count(), 1)
        self.assertEqual(PulaarEntry.objects.count(), n + 1)

    def test_rejet_ne_publie_rien(self):
        n = PulaarEntry.objects.count()
        p = PulaarProposal.objects.create(term_lemma="x", definition_ff="def ok", status="rejete")
        self.assertEqual(PulaarEntry.objects.count(), n)
        self.assertIsNone(p.published_term)


class AdminEntreeTests(DictionnaireBase):
    """Le lexicographe ne peut pas valider une entrée sans définition pulaar :
    message clair dans l'admin, pas d'erreur 500."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser("adm", "a@b.c", "x")
        self.client.login(username="adm", password="x")

    def donnees(self, statut, sens=""):
        d = {
            "lemma": "hoore", "dialect": self.fuf.pk, "pos": self.nom.pk, "homonym_index": 1,
            "source": self.libre.pk, "status": statut,
            "senses-TOTAL_FORMS": 1 if sens else 0, "senses-INITIAL_FORMS": 0,
            "senses-MIN_NUM_FORMS": 0, "senses-MAX_NUM_FORMS": 1000,
            "examples-TOTAL_FORMS": 0, "examples-INITIAL_FORMS": 0, "examples-MIN_NUM_FORMS": 0, "examples-MAX_NUM_FORMS": 1000,
            "translations-TOTAL_FORMS": 0, "translations-INITIAL_FORMS": 0, "translations-MIN_NUM_FORMS": 0,
            "translations-MAX_NUM_FORMS": 1000,
        }
        if sens:
            d.update({"senses-0-text": sens, "senses-0-ORDER": 1, "senses-0-DELETE": "", "senses-0-id": ""})
        return d

    def test_validation_sans_sens_refusee(self):
        r = self.client.post("/admin/snippets/pulaar/pulaarentry/add/", self.donnees("validated"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "sans définition en pulaar")
        self.assertFalse(PulaarEntry.objects.filter(lemma="hoore").exists())

    def test_validation_avec_sens_acceptee(self):
        r = self.client.post("/admin/snippets/pulaar/pulaarentry/add/", self.donnees("validated", "Cifol cuuɗi"))
        self.assertEqual(r.status_code, 302, r.content.decode()[:3000] if r.status_code != 302 else "")
        e = PulaarEntry.objects.get(lemma="hoore")
        self.assertEqual(e.status, "validated")
        self.assertEqual(e.senses.count(), 1)
