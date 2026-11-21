from django.test import TestCase


class PartageTests(TestCase):
    def test_pages_de_service_ont_un_apercu(self):
        for url, titre in (("/meteo/", "Météo"), ("/revue-de-presse/", "Revue de presse"), ("/convertisseur/", "Convertisseur de devises")):
            r = self.client.get(url)
            self.assertContains(r, f'<meta property="og:title" content="{titre}">', html=False)
            self.assertContains(r, 'property="og:image"')
            self.assertContains(r, "partage")  # image par défaut
            self.assertContains(r, 'rel="canonical"')
            self.assertContains(r, 'name="twitter:card"')

    def test_accueil_a_une_description(self):
        r = self.client.get("/")
        self.assertContains(r, 'property="og:description"')
        self.assertContains(r, 'property="og:site_name" content="Kaloum24"')
