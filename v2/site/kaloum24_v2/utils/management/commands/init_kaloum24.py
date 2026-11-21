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

SOURCES_PRESSE = [  # nom, site, flux, actif, note
    ("Guinéenews", "https://guineenews.org", "https://guineenews.org/feed/", True, "Flux RSS public ; extrait + lien."),
    ("Mosaïque Guinée", "https://mosaiqueguinee.com", "https://mosaiqueguinee.com/feed/", True, "Flux RSS public ; extrait + lien."),
    ("Guinée360", "https://www.guinee360.com", "https://www.guinee360.com/feed/", True, "Flux RSS public ; extrait + lien."),
    ("Vision Guinée", "https://www.visionguinee.info", "https://www.visionguinee.info/feed/", True, "Flux RSS public ; extrait + lien."),
    ("Guinée Matin", "https://guineematin.com", "https://guineematin.com/feed/", True, "Flux RSS public ; extrait + lien."),
    ("Le Jour Guinée", "https://www.lejourguinee.com", "https://www.lejourguinee.com/feed/", True, "Flux RSS public ; extrait + lien."),
    ("Le Révélateur 224", "https://www.lerevelateur224.com", "https://www.lerevelateur224.com/feed/", True, "Flux RSS public ; extrait + lien."),
    ("Fouta Ka Meen", "https://foutakameen.com", "https://foutakameen.com/feed/", True, "Flux RSS public (WordPress) ; extrait + lien. Actualité du Fouta."),
    ("Kumpital", "https://kumpital.com", "https://kumpital.com/feed/", True, "Flux RSS public (WordPress) ; extrait + lien. Publie rarement."),
    ("RFI Fulfulde", "https://www.rfi.fr/ff/", "https://www.rfi.fr/ff/rss", True,
     "Activé à la demande du responsable éditorial. Titres en fulfulde, non traduits ; extrait + lien. Conditions de réutilisation RFI à confirmer."),
    ("RFI Afrique", "https://www.rfi.fr/fr/afrique/", "https://www.rfi.fr/fr/afrique/rss", False,
     "DÉSACTIVÉ : conditions de réutilisation des flux RFI à vérifier (usage commercial). Activer seulement après accord."),
]

RUBRIQUES = ["Politique", "Économie", "Société", "Afrique", "Culture", "Sport", "Pulaar",
             "Faits divers", "Régions", "Mines & Énergie", "Opinions & Tribunes"]
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
        self._pages_cadre(home)
        self._sources_presse()

        groupe, _ = Group.objects.get_or_create(name="Lexicographes Pulaar")
        perms = Permission.objects.filter(content_type__app_label="pulaar") | Permission.objects.filter(
            codename="access_admin"
        )
        groupe.permissions.set(perms)

        self._roles(NewsListingPage.objects.first())
        try:
            self._placeholder()
        except Exception as exc:  # le stockage ne doit jamais bloquer un déploiement
            self.stderr.write(f"Image par défaut non restaurée : {exc}")
        self._admin()
        self.stdout.write("Initialisation Kaloum24 terminée.")

    def _pages_cadre(self, home):
        """Charte, mentions légales, à propos : créées UNE fois, en brouillon (non publiées).
        Jamais réécrites ensuite : l'équipe les complète dans l'administration."""
        import json

        from kaloum24_v2.standardpages.models import StandardPage
        from kaloum24_v2.utils.data.pages_cadre import PAGES

        for doc in PAGES:
            if StandardPage.objects.filter(slug=doc["slug"]).exists():
                continue
            page = StandardPage(title=doc["title"], slug=doc["slug"], introduction=doc["introduction"],
                                body=json.dumps(doc["body"]), live=False)
            home.add_child(instance=page)
            page.save_revision()
            self.stdout.write(f"Brouillon créé : {doc['title']}")

    def _groupe(self, ancien, nouveau):
        """Renomme un groupe Wagtail d'origine en français. Renvoie (groupe, neuf) ;
        « neuf » vaut True seulement la première fois : on ne réécrit jamais des
        droits que l'administrateur aurait ajustés depuis."""
        if Group.objects.filter(name=nouveau).exists():
            return Group.objects.get(name=nouveau), False
        groupe = Group.objects.filter(name=ancien).first()
        if groupe:
            groupe.name = nouveau
            groupe.save()
            return groupe, True
        return Group.objects.create(name=nouveau), True

    def _roles(self, listing):
        """Deux rôles de rédaction, limités à la rubrique « Actualités » :
        Rédacteurs (écrivent et soumettent) et Relecteurs (relisent et publient)."""
        from wagtail.models import GroupPagePermission, GroupApprovalTask, Task, Workflow

        if listing is None:
            return
        redacteurs, r_neuf = self._groupe("Editors", "Rédacteurs")
        relecteurs, l_neuf = self._groupe("Moderators", "Relecteurs")

        def droit(code):
            return Permission.objects.get(content_type__app_label="wagtailcore",
                                          content_type__model="page", codename=code)

        if r_neuf or l_neuf:
            for groupe, codes in ((redacteurs, ["add_page", "change_page"]),
                                  (relecteurs, ["add_page", "change_page", "publish_page",
                                                "lock_page", "unlock_page"])):
                GroupPagePermission.objects.filter(group=groupe, page__depth=1).delete()  # fin des droits sur tout le site
                for code in codes:
                    GroupPagePermission.objects.get_or_create(group=groupe, page=listing, permission=droit(code))
            for groupe in (redacteurs, relecteurs):
                groupe.permissions.add(*Permission.objects.filter(
                    content_type__app_label="wagtailadmin", codename="access_admin"))

            Workflow.objects.filter(name="Moderators approval").update(name="Relecture éditoriale")
            for tache in Task.objects.filter(name="Moderators approval"):
                tache.name = "Relecture par un relecteur"
                tache.save()

    def _placeholder(self):
        """Recopie l'image par défaut dans le stockage si son fichier a disparu
        (disque éphémère de Render avant le branchement de Supabase Storage)."""
        from django.contrib.staticfiles.finders import find
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage

        from kaloum24_v2.images.models import CustomImage

        chemin = find("images/placeholder-image.webp")
        if not chemin:
            return
        with open(chemin, "rb") as f:
            contenu = f.read()
        for image in CustomImage.objects.filter(tags__name="placeholder"):
            if image.file and not default_storage.exists(image.file.name):
                # Écriture directe : évite le recalcul des dimensions sur un fichier absent.
                # Extension .webp obligatoire : le bucket n'accepte que des types MIME connus.
                nom = default_storage.save("original_images/placeholder-image.webp", ContentFile(contenu))
                CustomImage.objects.filter(pk=image.pk).update(file=nom)
                image.renditions.all().delete()
                self.stdout.write(f"Image par défaut restaurée : {nom}")

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

    def _sources_presse(self):
        """Sources de départ (flux RSS publics testés le 2026-11-21). Créées une seule fois ; modifiables dans l'admin."""
        from kaloum24_v2.news.models import SourcePresse

        for nom, site, flux, actif, note in SOURCES_PRESSE:
            SourcePresse.objects.get_or_create(
                flux=flux, defaults={"nom": nom, "site": site, "actif": actif, "note": note,
                                     "langue": "ff" if "/ff/" in flux else "fr"})
