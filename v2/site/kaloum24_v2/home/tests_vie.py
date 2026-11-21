from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from kaloum24_v2.home import meteo as m
from kaloum24_v2.news.models import Breve

FAUX = [{"nom": "Conakry", "temperature": 29, "libelle": "Ciel dégagé", "symbole": "☀️"}]


class VieDuSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("init_kaloum24", verbosity=0)

    def setUp(self):
        cache.clear()

    def test_bandeau_sur_toutes_les_pages_sans_meteo(self):
        with mock.patch.object(m, "_une_ville", side_effect=OSError("réseau coupé")):
            for url in ("/", "/actualites/"):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, url)
                self.assertContains(r, "vie-barre")
                self.assertContains(r, "data-vie-heure")

    def test_message_neutre_si_aucune_info(self):
        with mock.patch.object(m, "_telecharger", return_value=[]):
            self.assertContains(self.client.get("/"), "Bienvenue sur Kaloum24")

    def test_breves_dans_le_defilement(self):
        Breve.objects.create(texte="Information flash de test")
        with mock.patch.object(m, "_telecharger", return_value=[]):
            self.assertContains(self.client.get("/"), "Information flash de test")

    def test_meteo_affichee_avec_attribution(self):
        with mock.patch.object(m, "_telecharger", return_value=FAUX):
            r = self.client.get("/")
        self.assertContains(r, "29°C")
        self.assertContains(r, "MET Norway")

    def test_meteo_cache_et_secours(self):
        with mock.patch.object(m, "_telecharger", return_value=FAUX) as ok:
            m.meteo(); m.meteo()
            self.assertEqual(ok.call_count, 1)
        cache.delete(m.CLE)
        with mock.patch.object(m, "_une_ville", side_effect=OSError("panne")):
            self.assertEqual(m.meteo(), FAUX)  # dernière valeur connue

    def test_respect_mouvement_reduit(self):
        css = open(__import__("django.contrib.staticfiles.finders", fromlist=["find"]).find("home/vie.css")).read()
        self.assertIn("prefers-reduced-motion", css)


class MetNorwayTests(TestCase):
    def test_symboles(self):
        self.assertEqual(m._decrire("clearsky_day"), ("Ciel dégagé", "☀️"))
        self.assertEqual(m._decrire("lightrainshowers_night")[0], "Averses")
        self.assertEqual(m._decrire("rainandthunder")[0], "Orage")
        self.assertEqual(m._decrire("heavyrain")[0], "Forte pluie")
        self.assertEqual(m._decrire(None)[0], "Variable")

    def test_analyse_reponse(self):
        import io, json as j
        rep = {"properties": {"timeseries": [{"data": {"instant": {"details": {"air_temperature": 30.1}},
               "next_1_hours": {"summary": {"symbol_code": "partlycloudy_day"}}}}]}}
        faux = io.BytesIO(j.dumps(rep).encode())
        faux.__enter__ = lambda s: s
        faux.__exit__ = lambda *a: None
        with mock.patch("urllib.request.urlopen", return_value=faux):
            v = m._une_ville(("Conakry", 9.5, -13.6, "Guinée"))
        self.assertEqual(v["temperature"], 30)
        self.assertEqual(v["libelle"], "Partiellement nuageux")
