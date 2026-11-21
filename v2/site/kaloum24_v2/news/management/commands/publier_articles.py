"""Importe et publie les articles décrits dans news/data/articles/*.json.

Idempotent et respectueux du travail de l'équipe : un article n'est écrit qu'UNE
fois (repéré par une entrée d'historique « Import d'un article »). Si la page existe
déjà (même adresse, ou « ancien_slug »), son contenu est remplacé par une nouvelle
version — les versions précédentes restent dans l'historique — mais sa signature,
sa rubrique et ses réglages sont conservés. Une page absente est créée.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import PageLogEntry, Site

from kaloum24_v2.news.models import ArticlePage, NewsListingPage
from kaloum24_v2.utils.models import ArticleTopic, AuthorSnippet

DOSSIER = Path(__file__).resolve().parents[2] / "data" / "articles"
ACTION = "kaloum24.import"


class Command(BaseCommand):
    help = "Importe et publie les articles du dossier news/data/articles (une seule fois chacun)."

    def handle(self, *args, **options):
        listing = NewsListingPage.objects.first()
        if listing is None:
            self.stderr.write("Pas de page « Actualités » : lancer init_kaloum24 d'abord.")
            return
        for fichier in sorted(DOSSIER.glob("*.json")):
            doc = json.loads(fichier.read_text(encoding="utf-8"))
            with transaction.atomic():
                self._importer(listing, doc)

    def _importer(self, listing, doc):
        page = (ArticlePage.objects.filter(slug=doc["slug"]).first()
                or ArticlePage.objects.filter(slug=doc.get("ancien_slug", "")).first())
        if page and PageLogEntry.objects.filter(page=page, action=ACTION).exists():
            self.stdout.write(f"« {doc['title']} » : déjà importé, rien à faire.")
            return

        ancienne_adresse = None
        if page is None:
            page = ArticlePage(
                title=doc["title"], slug=doc["slug"],
                topic=ArticleTopic.objects.get(title=doc["rubrique"]),
                author=AuthorSnippet.objects.get(title=doc["signature"]),
            )
            page.introduction, page.body = doc["introduction"], json.dumps(doc["body"])
            listing.add_child(instance=page)
        else:
            ancienne_adresse = page.url_path
            page.title, page.slug, page.introduction = doc["title"], doc["slug"], doc["introduction"]
            page.body = json.dumps(doc["body"])
            page.save()

        revision = page.save_revision(log_action=ACTION)
        revision.publish()
        if ancienne_adresse and not ancienne_adresse.endswith(f"/{doc['slug']}/"):
            self._rediriger(page, ancienne_adresse)
        self.stdout.write(f"« {doc['title']} » publié ({page.url_path}).")

    def _rediriger(self, page, ancienne_url_path):
        site = Site.objects.filter(is_default_site=True).first()
        racine = site.root_page.url_path if site else "/"
        relative = "/" + ancienne_url_path[len(racine):] if ancienne_url_path.startswith(racine) else ancienne_url_path
        Redirect.objects.get_or_create(
            old_path=Redirect.normalise_path(relative), site=site,
            defaults={"redirect_page": page, "is_permanent": True},
        )
