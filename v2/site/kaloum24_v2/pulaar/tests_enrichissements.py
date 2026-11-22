"""Prononciation, son, image, étymologie, liens entre entrées : visibilité et affichage."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.images.tests.utils import get_test_image_file

from .models import (PulaarAudio, PulaarDialect, PulaarEntry, PulaarImage, PulaarPos, PulaarPronunciation,
                     PulaarRelation, PulaarSense, PulaarSource)


@override_settings(MEDIA_ROOT="/tmp/k24-test-media")
class EnrichissementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pulaar", verbosity=0)
        libre = PulaarSource.objects.create(name="Libre", rights_status="open_license")
        cls.prive = PulaarSource.objects.create(name="À vérifier", rights_status="to_check")
        d, nom = PulaarDialect.objects.get(code="fuf"), PulaarPos.objects.get(code="nom")

        def e(lemma, src=libre):
            x = PulaarEntry.objects.create(lemma=lemma, dialect=d, pos=nom, source=src)
            PulaarSense.objects.create(entry=x, text=f"def {lemma}")
            return x

        cls.mot = e("Hoddu")
        cls.pluriel = e("Hoddi")
        cls.contraire = e("Naange")
        cls.cache = e("Secret", cls.prive)  # non public
        PulaarPronunciation.objects.create(entry=cls.mot, ipa="[hod.du]")
        cls.doc = Document.objects.create(title="son", file=ContentFile(b"ID3", name="hoddu.mp3"))
        cls.audio_ok = PulaarAudio.objects.create(entry=cls.mot, audio=cls.doc, speaker="Mariama", consent_given=True)
        cls.audio_sans = PulaarAudio.objects.create(entry=cls.mot, audio=cls.doc, speaker="Inconnu")
        img = Image.objects.create(title="i", file=get_test_image_file())
        cls.img_ok = PulaarImage.objects.create(entry=cls.mot, image=img, caption="Un hoddu", credit="Photo X, CC0", rights_ok=True)
        cls.img_sans = PulaarImage.objects.create(entry=cls.mot, image=img, caption="Image sans droits")
        PulaarRelation.objects.create(entry=cls.mot, kind="plural", target=cls.pluriel)
        PulaarRelation.objects.create(entry=cls.mot, kind="antonym", target=cls.contraire)
        PulaarRelation.objects.create(entry=cls.mot, kind="synonym", target=cls.cache)
        cls.mot.etymology = "Mot du fonds ancien."
        cls.mot.origin = "inherited"
        cls.mot.usage_note = "Se dit surtout des maisons."
        cls.mot.save()
        cls.admin = get_user_model().objects.create_superuser("adm", "a@b.c", "x")

    def page(self, e):
        return self.client.get(reverse("pulaar:terme", args=[e.slug]))

    def test_public_voit_ce_qui_est_autorise(self):
        r = self.page(self.mot)
        self.assertContains(r, "[hod.du]")
        self.assertContains(r, "Mariama")
        self.assertNotContains(r, "Inconnu")  # sans consentement
        self.assertContains(r, "Un hoddu")
        self.assertContains(r, "Photo X, CC0")
        self.assertNotContains(r, "Image sans droits")
        self.assertContains(r, "Mot hérité")
        self.assertContains(r, "Mot du fonds ancien.")
        self.assertContains(r, "Se dit surtout des maisons.")

    def test_liens_visibles_seulement(self):
        r = self.page(self.mot)
        self.assertContains(r, "Hoddi")
        self.assertContains(r, "Naange")
        self.assertContains(r, "Pluriel")
        self.assertContains(r, "Contraire")
        self.assertNotContains(r, "Secret")  # entrée non publique : jamais citée au public

    def test_lien_inverse_sur_lentree_liee(self):
        r = self.page(self.pluriel)
        self.assertContains(r, "Singulier")
        self.assertContains(r, "Hoddu")
        self.assertContains(self.page(self.contraire), "Contraire")  # symétrique

    def test_equipe_voit_tout_marque_non_public(self):
        self.client.login(username="adm", password="x")
        r = self.page(self.mot)
        self.assertContains(r, "Inconnu")
        self.assertContains(r, "Image sans droits")
        self.assertContains(r, "Secret")
        self.assertContains(r, "Non public")

    def test_rien_daffiche_quand_vide(self):
        r = self.page(self.contraire)
        for mot in ("Origine", "Note d'usage", "Écouter", "<figure"):
            self.assertNotContains(r, mot)

    def test_lien_vers_soi_meme_refuse(self):
        with self.assertRaises(ValidationError):
            PulaarRelation(entry=self.mot, kind="synonym", target=self.mot).clean()

    def test_admin_ajout_entree_avec_enrichissements(self):
        self.client.login(username="adm", password="x")
        r = self.client.get("/admin/snippets/pulaar/pulaarentry/edit/%d/" % self.mot.pk)
        self.assertEqual(r.status_code, 200)
        for t in ("Prononciation (API)", "Enregistrement audio", "Illustration", "étymologie"):
            self.assertContains(r, t)
