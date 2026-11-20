"""Initialisation idempotente de Kaloum24, exécutée à chaque déploiement.

Crée uniquement ce qui manque : page d'accueil, page « Actualités », rubriques,
signature de la rédaction, groupe « Lexicographes Pulaar », compte administrateur
(si ADMIN_* est défini ET qu'aucun superutilisateur n'existe). N'invente aucun
article, ne réinitialise jamais un mot de passe existant.
"""
import os
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Site

from kaloum24_v2.home.models import HomePage
from kaloum24_v2.news.models import NewsListingPage
from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet

RUBRIQUES = ["Politique", "Économie", "Société", "Afrique", "Culture", "Sport", "Pulaar"]
INTRO = "L'actualité de Guinée et d'Afrique de l'Ouest, rédigée à Conakry."


class Command(BaseCommand):
    help = "Crée la structure de base du site (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        home = HomePage.objects.first()
        if home is None:
            self.stderr.write("Aucune HomePage : migrations non appliquées ?")
            return
        if home.title != "Kaloum24":
            home.title, home.introduction = "Kaloum24", INTRO
            home.save_revision().publish()

        site = Site.objects.filter(is_default_site=True).first()
        if site:
            url = os.environ.get("SITE_URL") or os.environ.get("RENDER_EXTERNAL_URL")
            if url:
                parts = urlsplit(url)
                site.hostname = parts.hostname
                site.port = parts.port or (443 if parts.scheme == "https" else 80)
            site.site_name, site.root_page_id = "Kaloum24", home.pk
            site.save()

        if not NewsListingPage.objects.exists():
            listing = NewsListingPage(title="Actualités", slug="actualites", introduction=f"<p>{INTRO}</p>")
            home.add_child(instance=listing)
            listing.save_revision().publish()

        self._navigation(site, NewsListingPage.objects.first())

        for titre in RUBRIQUES:
            ArticleTopic.objects.get_or_create(title=titre)
        AuthorSnippet.objects.get_or_create(title="Rédaction Kaloum24")

        groupe, _ = Group.objects.get_or_create(name="Lexicographes Pulaar")
        perms = Permission.objects.filter(content_type__app_label="pulaar") | Permission.objects.filter(
            codename="access_admin"
        )
        groupe.permissions.set(perms)

        self._admin()
        self.stdout.write("Initialisation Kaloum24 terminée.")

    def _navigation(self, site, listing):
        from kaloum24_v2.navigation.models import NavigationSettings

        if not (site and listing):
            return
        reglages = NavigationSettings.for_site(site)
        if not reglages.primary_navigation:
            reglages.primary_navigation = [("link", {"page": listing, "title": "Actualités"})]
            reglages.save()

    def _admin(self):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            return
        nom, mot_de_passe = os.environ.get("ADMIN_USERNAME"), os.environ.get("ADMIN_PASSWORD")
        if not (nom and mot_de_passe):
            self.stdout.write("Pas de superutilisateur : définir ADMIN_USERNAME / ADMIN_PASSWORD, "
                              "ou lancer createsuperuser.")
            return
        User.objects.create_superuser(nom, os.environ.get("ADMIN_EMAIL", ""), mot_de_passe)
        self.stdout.write(f"Superutilisateur « {nom} » créé.")
