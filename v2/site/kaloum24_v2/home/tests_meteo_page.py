from unittest import mock

from django.test import TestCase


class MeteoPageTests(TestCase):
    def test_regroupe_par_pays(self):
        villes = [{"nom": "Conakry", "pays": "Guinée", "temperature": 29, "libelle": "Couvert", "symbole": "x"},
                  {"nom": "Dakar", "pays": "Sénégal", "temperature": 27, "libelle": "Dégagé", "symbole": "x"}]
        with mock.patch("kaloum24_v2.home.meteo.meteo", return_value=villes):
            r = self.client.get("/meteo/")
        self.assertContains(r, "Guinée")
        self.assertContains(r, "Sénégal")
        self.assertContains(r, "MET Norway")

    def test_panne_sans_erreur(self):
        with mock.patch("kaloum24_v2.home.meteo.meteo", return_value=[]):
            r = self.client.get("/meteo/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "momentanément indisponible")
