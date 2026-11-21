from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase

from kaloum24_v2.prix import change
from kaloum24_v2.prix.models import TauxChange

PDF_PYPDF = "DEVISES CONTRE GNF AU 20/11/2026DGCC/DOC/SM/TK/\nListe N°0221/2026\nDollar Des USA 8839.0137USD\nEURO 9715.8494EUR\nFranc Cfa Ouest Africain 14.8193XOF\nDroits de Tirage Spéciaux 11883.0142DTS"
PDF_ANCIEN = "DEVISES CONTRE GNF AU 19/09/2025\nDollar Etats-Unis  USD         8 650,9703\nEuro  EUR       10 155,3791\nFranc C.F.A.      XOF              15,2094"


class AnalyseTests(TestCase):
    def test_format_nombre_colle_au_code(self):
        jour, c = change.analyser(PDF_PYPDF)
        self.assertEqual(jour, date(2026, 11, 20))
        self.assertEqual(c["USD"], Decimal("8839.0137"))
        self.assertEqual(c["XOF"], Decimal("14.8193"))
        self.assertNotIn("DTS", c)

    def test_ancien_format_avec_espaces(self):
        jour, c = change.analyser(PDF_ANCIEN)
        self.assertEqual(c["EUR"], Decimal("10155.3791"))

    def test_texte_inconnu(self):
        self.assertEqual(change.analyser("rien"), (None, {}))

    def test_conversion_via_gnf(self):
        c = {"USD": Decimal("8800"), "XOF": Decimal("15")}
        self.assertEqual(change.convertir(Decimal(2), "USD", "GNF", c), Decimal(17600))
        self.assertEqual(change.convertir(Decimal(8800), "GNF", "USD", c), Decimal(1))
        self.assertIsNone(change.convertir(Decimal(1), "ABC", "GNF", c))


class ImportTests(TestCase):
    def test_import_refuse_un_pdf_hors_bcrg(self):
        corps = '[{"content":{"rendered":"\\"source\\":\\"https:\\\\/\\\\/exemple.com\\\\/x.pdf\\""}}]'
        with mock.patch.object(change, "_get", return_value=corps.encode()):
            self.assertEqual(change.url_dernier_pdf(), "")

    def test_import_enregistre_et_ignore_un_pdf_inattendu(self):
        with mock.patch.object(change, "url_dernier_pdf", return_value=change.PREFIXE_PDF + "a.pdf"), \
                mock.patch.object(change, "_get", return_value=b""), mock.patch.object(change, "lire_pdf", return_value=PDF_PYPDF):
            self.assertEqual(change.importer(), 3)
            self.assertEqual(change.importer(), 0)  # idempotent
        with mock.patch.object(change, "url_dernier_pdf", return_value=change.PREFIXE_PDF + "b.pdf"), \
                mock.patch.object(change, "_get", return_value=b""), mock.patch.object(change, "lire_pdf", return_value="format inconnu"):
            self.assertEqual(change.importer(), 0)


class PageTests(TestCase):
    def test_sans_cours(self):
        r = self.client.get("/convertisseur/")
        self.assertContains(r, "pas encore disponible")

    def test_conversion_affichee_avec_date_et_source(self):
        TauxChange.objects.create(date=date(2026, 11, 20), devise="EUR", cours=Decimal("9715.8494"), source_url=change.PREFIXE_PDF + "a.pdf")
        r = self.client.get("/convertisseur/", {"montant": "100", "de": "EUR", "vers": "GNF"})
        self.assertContains(r, "971")  # 971 584,94
        self.assertContains(r, "20 novembre 2026")
        self.assertContains(r, "document officiel")

    def test_montant_invalide(self):
        TauxChange.objects.create(date=date(2026, 11, 20), devise="EUR", cours=Decimal("9715.8494"))
        r = self.client.get("/convertisseur/", {"montant": "abc"})
        self.assertContains(r, "montant valide")
