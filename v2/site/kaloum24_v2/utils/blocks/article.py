"""Blocs de rédaction pour les articles de presse.

Le corps d'un article est une suite libre de paragraphes, d'intertitres, de
citations, d'images, d'encadrés et de vidéos. Les anciens blocs « section »,
« CTA » et « statistiques » restent valides pour ne pas casser les contenus déjà
saisis, mais ne sont plus proposés en premier.
"""
from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock

from .layout import CallToActionBlock, SectionBlock, StatisticSectionBlock


class ArticleImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(label="Image")
    image_alt_text = blocks.CharBlock(
        required=False,
        label="Texte alternatif",
        help_text="Décrit l'image pour les personnes qui ne la voient pas. Si vide, le texte alternatif de l'image est utilisé.",
    )
    caption = blocks.CharBlock(required=False, label="Légende")
    credit = blocks.CharBlock(required=False, label="Crédit photo", help_text="Ex. : Photo Mamadou Diallo / Kaloum24")

    class Meta:
        icon = "image"
        label = "Image"
        template = "components/streamfield/blocks/article_image_block.html"


class ArticleQuoteBlock(blocks.StructBlock):
    quote = blocks.TextBlock(label="Citation")
    attribution = blocks.CharBlock(required=False, label="Qui parle ? (nom, fonction)")

    class Meta:
        icon = "openquote"
        label = "Citation"
        template = "components/streamfield/blocks/article_quote_block.html"


class ArticleBoxBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Titre de l'encadré")
    text = blocks.RichTextBlock(features=["bold", "italic", "link", "ol", "ul"], label="Texte")

    class Meta:
        icon = "info-circle"
        label = "Encadré"
        template = "components/streamfield/blocks/article_box_block.html"


class ArticleBody(blocks.StreamBlock):
    paragraph = blocks.RichTextBlock(
        features=["bold", "italic", "link", "ol", "ul"],
        label="Paragraphe",
        icon="pilcrow",
        template="components/streamfield/blocks/article_paragraph_block.html",
    )
    subheading = blocks.CharBlock(
        label="Intertitre",
        icon="title",
        template="components/streamfield/blocks/article_subheading_block.html",
    )
    quote = ArticleQuoteBlock()
    image = ArticleImageBlock()
    box = ArticleBoxBlock()
    video = EmbedBlock(
        label="Vidéo ou publication (YouTube, Facebook, X…)",
        help_text="Collez l'adresse (URL) de la vidéo ou de la publication.",
        icon="media",
        template="components/streamfield/blocks/article_video_block.html",
    )
    table = TableBlock(
        label="Tableau",
        icon="table",
        help_text="Cochez « En-tête de colonne » pour que la première ligne serve de titres. Idéal pour des chiffres, résultats ou calendriers.",
    )
    # Anciens blocs, conservés pour les contenus existants.
    section = SectionBlock(label="Section (ancien format)")
    cta = CallToActionBlock(label="Appel à l'action (ancien format)")
    statistics = StatisticSectionBlock(label="Statistiques (ancien format)")

    class Meta:
        template = "components/streamfield/article_body.html"
