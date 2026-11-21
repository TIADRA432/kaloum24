import json

from django.test import TestCase


class PwaTests(TestCase):
    def test_manifeste(self):
        r = self.client.get("/manifest.webmanifest")
        self.assertEqual(r["Content-Type"], "application/manifest+json")
        d = json.loads(r.content)
        self.assertEqual(d["name"], "Kaloum24")
        self.assertEqual(d["display"], "standalone")
        self.assertTrue(any(i["purpose"] == "maskable" for i in d["icons"]))

    def test_service_worker(self):
        r = self.client.get("/sw.js")
        self.assertEqual(r.status_code, 200)
        self.assertIn("javascript", r["Content-Type"])
        self.assertEqual(r["Cache-Control"], "no-cache")
        body = r.content.decode()
        self.assertIn("/hors-ligne/", body)
        self.assertIn("EXCLUS", body)
        self.assertIn("admin", body)  # l'admin et les recherches ne sont jamais mis en cache

    def test_page_hors_ligne_et_balises(self):
        r = self.client.get("/hors-ligne/")
        self.assertContains(r, "hors ligne")
        self.assertContains(r, 'rel="manifest"')
        self.assertContains(r, 'content="#1E2B63"')
        self.assertContains(r, "serviceWorker")
