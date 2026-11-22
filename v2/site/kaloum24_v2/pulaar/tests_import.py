"""Import d'un lot : nettoyage du mot vedette, droits, idempotence, aperçu équipe, page d'admin.
Les données sont factices (mots « mot-a », « def a ») : le vrai dictionnaire n'est jamais dans le dépôt."""
import json
from collections import Counter

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .importer import ImportInvalide, importer, nettoyer, retirer_lot
from .models import PulaarEntry, PulaarImportBatch, PulaarNounClass, PulaarSource

CLASSES = {"ndee", "ngal", "ngol"}


def stats():
    return Counter()


def entree(lemma, texte="def a", pos="nom", classe=None, **kw):
    return {"lemma": lemma, "slug": "x", "dialect_code": "fuc", "pos_code": pos, "homonym_index": 1,
            "noun_class_marker": classe, "senses": [{"sort_order": 1, "text": texte, "source_locator": "p. 1"}],
            "examples": kw.get("examples", [])}


def lot(entries, droits="permission_granted"):
    return {"source": {"name": "Source factice", "method": "pdf_extraction", "rights_status": droits,
                       "rights_note": "note"}, "entries": entries}


def envoyer(data):
    brut = json.dumps(data).encode()
    return brut, importer(data, brut, "lot_test.json")


class NettoyageTests(TestCase):
    def test_formes_multiples_deviennent_variantes(self):
        r = nettoyer(entree("mot-a: mot-b"), CLASSES, stats())
        self.assertEqual((r["lemma"], r["variants"]), ("mot-a", ["mot-b"]))
        r = nettoyer(entree("mot-a,mot-c ; mot-a ; mot-d"), CLASSES, stats())
        self.assertEqual((r["lemma"], r["variants"]), ("mot-a", ["mot-c", "mot-d"]))

    def test_forme_collee_en_tete_de_definition(self):
        r = nettoyer(entree("mot-a", "mot-bbb: (ndee) def a"), CLASSES, stats())
        self.assertEqual((r["lemma"], r["variants"], r["noun_class_marker"], r["senses"][0]["text"]),
                         ("mot-a", ["mot-bbb"], "ndee", "def a"))

    def test_mot_coupe_par_le_saut_de_ligne_est_recolle(self):
        r = nettoyer(entree("mot-a", "l: (ngol) def a"), CLASSES, stats())
        self.assertEqual((r["lemma"], r["variants"], r["noun_class_marker"]), ("mot-al", [], "ngol"))

    def test_parenthese_coupee_entre_mot_et_definition(self):
        r = nettoyer(entree("mot-a: (", "ndee) def a", pos="a-preciser"), CLASSES, stats())
        self.assertEqual((r["lemma"], r["noun_class_marker"], r["senses"][0]["text"]), ("mot-a", "ndee", "def a"))
        r = nettoyer(entree("mot-a:(", "Gd) def a", pos="a-preciser"), CLASSES, stats())
        self.assertEqual((r["pos_code"], r["senses"][0]["text"]), ("verbe", "def a"))

    def test_le_texte_des_definitions_normales_nest_pas_touche(self):
        r = nettoyer(entree("mot-a", "ko: huunde (ndee) def"), CLASSES, stats())
        self.assertEqual(r["senses"][0]["text"], "ko: huunde (ndee) def")
        self.assertEqual(r["variants"], [])


class ImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)

    def test_droits_toujours_a_verifier_et_entrees_documentees(self):
        brut, lot_ = envoyer(lot([entree("mot-a")], droits="permission_granted"))
        src = PulaarSource.objects.get(name="Source factice")
        self.assertEqual(src.rights_status, "to_check")  # le fichier ne peut pas accorder de droits
        e = PulaarEntry.objects.get(lemma="mot-a")
        self.assertEqual((e.status, e.import_batch_id, e.dialect.code), ("documented", lot_.pk, "fuc"))
        self.assertEqual(e.senses.get().text, "def a")
        self.assertFalse(PulaarEntry.objects.publiques().filter(pk=e.pk).exists())
        self.assertEqual(len(lot_.file_sha256), 64)

    def test_idempotent(self):
        data = lot([entree("mot-a"), entree("mot-b")])
        envoyer(data)
        n = PulaarEntry.objects.count()
        lot2 = envoyer(data)[1]
        self.assertEqual(PulaarEntry.objects.count(), n)
        self.assertEqual((lot2.entries_created, lot2.entries_skipped), (0, 2))

    def test_variantes_classes_et_exemples_crees(self):
        ex = [{"sort_order": 1, "sense_number": 1, "text": "exemple a", "translation": "", "source_locator": "p. 1"}]
        envoyer(lot([entree("mot-a: mot-b", classe="ndee", examples=ex)]))
        e = PulaarEntry.objects.get(lemma="mot-a")
        self.assertEqual([v.form for v in e.variants.all()], ["mot-b"])
        self.assertEqual(e.noun_class.marker, "ndee")
        self.assertTrue(PulaarNounClass.objects.filter(marker="ndee", dialect__code="fuc").exists())
        self.assertEqual(e.examples.get().text, "exemple a")

    def test_collision_apres_nettoyage_donne_un_numero_dhomonyme(self):
        envoyer(lot([entree("mot-a", "def 1"), entree("mot-a: mot-b", "def 2")]))
        self.assertEqual(sorted(PulaarEntry.objects.filter(lemma="mot-a").values_list("homonym_index", flat=True)), [1, 2])
        n = PulaarEntry.objects.count()
        envoyer(lot([entree("mot-a", "def 1"), entree("mot-a: mot-b", "def 2")]))  # re-import : rien de plus
        self.assertEqual(PulaarEntry.objects.count(), n)

    def test_slug_unique_meme_avec_entree_existante(self):
        envoyer(lot([entree("aada")]))  # « aada » existe déjà (Wiktionary)
        slugs = list(PulaarEntry.objects.filter(lemma="aada").values_list("slug", flat=True))
        self.assertEqual(len(set(slugs)), 2)

    def test_fichier_invalide_ou_dialecte_inconnu(self):
        with self.assertRaises(ImportInvalide):
            importer({"nope": 1}, b"{}", "x.json")
        bad = lot([{**entree("mot-a"), "dialect_code": "zzz"}])
        with self.assertRaises(ImportInvalide):
            importer(bad, b"{}", "x.json")
        self.assertFalse(PulaarEntry.objects.filter(lemma="mot-a").exists())

    def test_retirer_un_lot(self):
        _, lot_ = envoyer(lot([entree("mot-a"), entree("mot-b")]))
        n = PulaarEntry.objects.count()
        retirer_lot(lot_)
        self.assertEqual(PulaarEntry.objects.count(), n - 2)
        lot_.refresh_from_db()
        self.assertEqual(lot_.status, "removed")

    def test_verifier_dictionnaire_reste_conforme(self):
        envoyer(lot([entree("mot-a")]))
        call_command("verifier_dictionnaire", stdout=__import__("io").StringIO())


class ApercuEquipeEtAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        envoyer(lot([entree("mot-a: mot-b")] + [entree(f"mot-{i:03d}") for i in range(120)]))
        cls.e = PulaarEntry.objects.get(lemma="mot-a")
        U = get_user_model()
        cls.admin = U.objects.create_superuser("adm", "a@b.c", "x")
        cls.simple = U.objects.create_user("simple", "s@b.c", "x")  # connecté, mais pas équipe

    def test_public_ne_voit_rien(self):
        self.assertEqual(self.client.get(reverse("pulaar:terme", args=[self.e.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("pulaar:accueil")), "mot-a")
        self.client.login(username="simple", password="x")
        self.assertEqual(self.client.get(reverse("pulaar:terme", args=[self.e.slug])).status_code, 404)

    def test_equipe_voit_avec_bandeau_variantes_et_pagination(self):
        self.client.login(username="adm", password="x")
        r = self.client.get(reverse("pulaar:terme", args=[self.e.slug]))
        self.assertContains(r, "Non public")
        self.assertContains(r, "Autres formes")
        self.assertContains(r, "mot-b")
        acc = self.client.get(reverse("pulaar:accueil"))
        self.assertContains(acc, "Aperçu équipe")
        self.assertContains(acc, "Page 1 sur 2")
        self.assertContains(self.client.get(reverse("pulaar:accueil"), {"page": 2}), "Page 2 sur 2")
        self.assertContains(self.client.get(reverse("pulaar:accueil"), {"q": "mot-b"}), "mot-a")  # recherche par variante

    def test_page_import_reservee_et_envoi(self):
        url = reverse("pulaar_import")
        self.assertNotEqual(self.client.get(url).status_code, 200)  # anonyme refusé
        self.client.login(username="adm", password="x")
        self.assertContains(self.client.get(url), "Importer un lot")
        data = lot([entree("mot-z")])
        f = SimpleUploadedFile("lot_z.json", json.dumps(data).encode(), content_type="application/json")
        r = self.client.post(url, {"fichier": f}, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertTrue(PulaarEntry.objects.filter(lemma="mot-z").exists())
        mauvais = SimpleUploadedFile("x.json", b"pas du json", content_type="application/json")
        r = self.client.post(url, {"fichier": mauvais}, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(r.status_code, 400)

    def test_retrait_via_admin(self):
        self.client.login(username="adm", password="x")
        lot_ = PulaarImportBatch.objects.first()
        r = self.client.post(reverse("pulaar_import_retirer", args=[lot_.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(PulaarEntry.objects.filter(lemma="mot-a").exists())
