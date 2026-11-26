"""Dictionnaire monolingue Pulaar (modèle « v6 », porté en Django).

Règles (voir docs/PLAN_DICTIONNAIRE_PULAAR.md) :
  D1  Le pulaar est la base : une entrée n'est « validée » que si elle a un sens
      (définition) rédigé EN PULAAR.
  D2  Les autres langues sont des mots de traduction, jamais des définitions ;
      chaque traduction peut pointer vers un dictionnaire externe, par une
      adresse construite à l'affichage (modèle + mot encodé, domaines autorisés).
  D3  La provenance est portée par le sens, l'exemple et la traduction ; chaque
      source a un statut de droits (« à vérifier » par défaut).
  D4  Ce qui vient d'un fichier ou d'une IA passe par une file de relecture
      humaine (PulaarProposal ; zone d'import complète en phase 3).
"""
from urllib.parse import quote, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.models import Orderable

from .admin_forms import EntryAdminForm
from .slug import cle_recherche, forme_exacte, slug_unique

SOURCE_COMMUNAUTE = "communaute"
DIALECTE_PAR_DEFAUT = "fuf"
CODE_ISO3 = RegexValidator(r"^[a-z]{3}$", "Code de langue ISO 639-3 : trois lettres minuscules (fra, eng, wol…).")

# Dictionnaires externes : on ne lie que vers ces domaines (et leurs sous-domaines).
DOMAINES_EXTERNES_AUTORISES = ("wiktionary.org", "wikipedia.org", "webonary.org")


class PulaarDomain(models.Model):
    """Domaine thématique (Technologie, Agriculture…) : créé depuis l'admin,
    jamais une liste figée dans le code."""

    name = models.CharField("nom", max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, editable=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "domaine"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unique(PulaarDomain, self.name, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PulaarDialect(models.Model):
    """Variété de la langue (Pular de Guinée, Pulaar du Sénégal, Fulfulde…).
    Le code est le code ISO 639-3 de la variété ; la liste vient de l'ISO, pas
    d'une invention du projet."""

    code = models.CharField("code ISO 639-3", max_length=10, unique=True)
    name = models.CharField("nom", max_length=120)
    region = models.CharField("région / pays", max_length=200, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "dialecte"

    def __str__(self):
        return f"{self.name} ({self.code})"


class PulaarPos(models.Model):
    """Classe grammaticale : une table (modifiable dans l'admin), pas du texte libre."""

    code = models.SlugField("code", max_length=30, unique=True)
    name_fr = models.CharField("nom en français", max_length=60)
    name_ff = models.CharField("nom en pulaar", max_length=60, blank=True,
                               help_text="Laisser vide tant qu'un locuteur ne l'a pas fourni.")
    is_verbal = models.BooleanField("verbe", default=False)

    class Meta:
        ordering = ["name_fr"]
        verbose_name = "classe grammaticale"
        verbose_name_plural = "classes grammaticales"

    def __str__(self):
        return self.name_fr


class PulaarNounClass(models.Model):
    """Classe nominale (24 à 26 selon les variétés). Structure seulement : la liste
    exacte vient d'une source citée, jamais de mémoire."""

    marker = models.CharField("marqueur", max_length=30)
    dialect = models.ForeignKey(PulaarDialect, verbose_name="dialecte", null=True, blank=True,
                                on_delete=models.PROTECT, related_name="noun_classes")
    note = models.TextField("description / source", blank=True)

    class Meta:
        ordering = ["marker"]
        verbose_name = "classe nominale"
        verbose_name_plural = "classes nominales"
        constraints = [models.UniqueConstraint(fields=["dialect", "marker"], name="uq_nounclass_dialect_marker")]

    def __str__(self):
        return self.marker


class PulaarSource(models.Model):
    """Provenance. Jamais de donnée sans source rattachée."""

    PUBLIC, LIBRE, ACCORD, EN_ATTENTE, A_VERIFIER, RESTREINT = (
        "public_domain", "open_license", "permission_granted", "permission_pending", "to_check", "restricted")
    DROITS = [
        (PUBLIC, "Domaine public"),
        (LIBRE, "Licence libre (ex. CC BY-SA)"),
        (ACCORD, "Autorisation obtenue"),
        (EN_ATTENTE, "Autorisation demandée"),
        (A_VERIFIER, "À vérifier"),
        (RESTREINT, "Restreinte"),
    ]
    PUBLIABLES = (PUBLIC, LIBRE, ACCORD)

    name = models.CharField("nom", max_length=200)
    url = models.URLField("lien", max_length=500, blank=True)
    license = models.CharField("licence", max_length=100, blank=True)
    method = models.CharField("méthode", max_length=30, help_text="wiktionary, import_manuel, communaute…")
    rights_status = models.CharField(
        "droits de réutilisation", max_length=30, choices=DROITS, default=A_VERIFIER,
        help_text="Information de travail, pas un avis juridique. Tant que c'est « à vérifier », "
                  "« demandée » ou « restreinte », les entrées de cette source ne sont pas affichées au public.")
    rights_note = models.TextField("note sur les droits", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "source"

    @property
    def is_publishable(self):
        return self.rights_status in self.PUBLIABLES

    def __str__(self):
        return self.name


class PulaarExternalDictionary(models.Model):
    """Dictionnaire externe vers lequel un mot de traduction peut pointer.
    Le lien est construit à l'affichage : aucune adresse de mot stockée en dur."""

    code = models.SlugField("code", max_length=30, unique=True)
    name = models.CharField("nom", max_length=100)
    language_code = models.CharField("langue (ISO 639-3)", max_length=3, validators=[CODE_ISO3])
    url_template = models.CharField(
        "modèle d'adresse", max_length=300,
        help_text="https://… avec {term} à l'endroit du mot. Domaines autorisés : "
                  + ", ".join(DOMAINES_EXTERNES_AUTORISES) + ".")
    notes = models.TextField("notes", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "dictionnaire externe"
        verbose_name_plural = "dictionnaires externes"

    def clean(self):
        if "{term}" not in self.url_template:
            raise ValidationError({"url_template": "Le modèle doit contenir {term}."})
        p = urlparse(self.url_template.replace("{term}", "x"))
        hote = (p.hostname or "").lower()
        if p.scheme != "https" or not any(hote == d or hote.endswith("." + d) for d in DOMAINES_EXTERNES_AUTORISES):
            raise ValidationError({"url_template": "Adresse en https vers un domaine autorisé uniquement."})

    def url_for(self, terme):
        """Adresse du mot, ou None si le modèle n'est pas sûr."""
        try:
            self.clean()
        except ValidationError:
            return None
        return self.url_template.replace("{term}", quote(terme.strip().replace(" ", "_"), safe=""))

    def __str__(self):
        return self.name


class PulaarImportBatch(models.Model):
    """Journal d'un import (D4) : d'où vient le fichier, quand, par qui, ce qui a été créé.
    Permet de retirer proprement tout un lot."""

    FAIT, RETIRE = "done", "removed"
    STATUTS = [(FAIT, "Importé"), (RETIRE, "Retiré")]

    source = models.ForeignKey("PulaarSource", verbose_name="source", on_delete=models.PROTECT,
                               related_name="import_batches")
    file_name = models.CharField("fichier", max_length=255)
    file_sha256 = models.CharField("empreinte SHA-256", max_length=64)
    parser_version = models.CharField("version du traitement", max_length=60)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                    on_delete=models.SET_NULL, related_name="+")
    imported_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField("statut", max_length=10, choices=STATUTS, default=FAIT)
    entries_created = models.PositiveIntegerField("entrées créées", default=0)
    entries_skipped = models.PositiveIntegerField("entrées déjà présentes", default=0)
    senses_created = models.PositiveIntegerField("sens créés", default=0)
    examples_created = models.PositiveIntegerField("exemples créés", default=0)
    variants_created = models.PositiveIntegerField("formes variantes créées", default=0)
    notes = models.TextField("notes (corrections appliquées…)", blank=True)

    class Meta:
        ordering = ["-imported_at"]
        verbose_name = "lot d'import"
        verbose_name_plural = "lots d'import"

    def __str__(self):
        return f"{self.file_name} ({self.imported_at:%Y-%m-%d})"


class EntreeQuerySet(models.QuerySet):
    def visibles_pour(self, user):
        """Public : `publiques()`. Équipe connectée (aperçu avant publication) : tout,
        y compris les sources aux droits non établis, avec bandeau « non public »."""
        if user is not None and user.is_authenticated and user.is_staff:
            return self.all()
        return self.publiques()

    def publiques(self):
        """Ce que voit le public : ni brouillon, ni source aux droits non établis."""
        return self.exclude(status=PulaarEntry.BROUILLON).filter(source__rights_status__in=PulaarSource.PUBLIABLES)


class PulaarEntry(ClusterableModel):
    """Une entrée du dictionnaire (lemme).

    « documenté » = vient d'une source ou d'une proposition acceptée ;
    « validé » = un lexicographe l'a confirmé ET elle a un sens en pulaar.
    Jamais présumé validé.
    """

    BROUILLON, DOCUMENTE, VALIDE = "draft", "documented", "validated"
    STATUTS = [(BROUILLON, "Brouillon (non public)"), (DOCUMENTE, "Documenté"), (VALIDE, "Validé")]

    lemma = models.CharField("mot (lemme)", max_length=200)
    slug = models.SlugField(max_length=220, unique=True, editable=False)
    dialect = models.ForeignKey(PulaarDialect, verbose_name="dialecte", on_delete=models.PROTECT,
                                related_name="entries")
    pos = models.ForeignKey(PulaarPos, verbose_name="classe grammaticale", on_delete=models.PROTECT,
                            related_name="entries")
    homonym_index = models.PositiveSmallIntegerField(
        "n° d'homonyme", default=1, help_text="1 par défaut ; 2, 3… pour des mots écrits pareil mais différents.")
    noun_class = models.ForeignKey(PulaarNounClass, verbose_name="classe nominale", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="entries")
    domain = models.ForeignKey(PulaarDomain, verbose_name="domaine", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="entries")
    # PROTECT volontaire : supprimer une source qui a encore des entrées doit
    # être bloqué, pas transformé en donnée orpheline.
    source = models.ForeignKey(PulaarSource, verbose_name="source", on_delete=models.PROTECT,
                               related_name="entries")
    status = models.CharField("statut", max_length=20, choices=STATUTS, default=DOCUMENTE)
    import_batch = models.ForeignKey(PulaarImportBatch, null=True, blank=True, editable=False,
                                     on_delete=models.SET_NULL, related_name="entries")
    # Enrichissements facultatifs : vides tant qu'un lexicographe ne les remplit pas, rien n'est affiché alors.
    ORIGINES = [("inherited", "Mot hérité (fonds peul)"), ("loan", "Emprunt"), ("unknown", "Origine inconnue")]
    origin = models.CharField("origine du mot", max_length=12, choices=ORIGINES, blank=True,
                              help_text="Choix du lexicographe. Jamais déduit automatiquement.")
    origin_language = models.CharField("langue d'origine (emprunt)", max_length=80, blank=True)
    etymology = models.TextField("étymologie", blank=True, help_text="Texte rédigé, avec ses sources.")
    usage_note = models.TextField("note d'usage", blank=True,
                                  help_text="Emploi, registre, remarque (rédigé par le lexicographe).")
    search_key = models.CharField(max_length=220, blank=True, default="", db_index=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = EntreeQuerySet.as_manager()
    base_form_class = EntryAdminForm

    class Meta:
        ordering = ["lemma"]
        verbose_name = "entrée"
        verbose_name_plural = "entrées"
        constraints = [models.UniqueConstraint(fields=["dialect", "lemma", "pos", "homonym_index"],
                                               name="uq_entry_homonym")]

    def a_un_sens(self):
        return any((s.text or "").strip() for s in self.senses.all())

    def save(self, *args, **kwargs):
        if self.status == self.VALIDE and not self.a_un_sens():
            raise ValidationError("Une entrée ne peut être validée sans définition en pulaar.")
        if not self.slug:
            self.slug = slug_unique(PulaarEntry, self.lemma, self.pk)
        self.search_key = cle_recherche(self.lemma)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.lemma


class PulaarSense(Orderable):
    """Un sens : définition rédigée en pulaar uniquement (la variété est celle de l'entrée)."""

    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="senses")
    text = models.TextField("définition en pulaar")
    source = models.ForeignKey(PulaarSource, verbose_name="source de la définition", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="senses",
                               help_text="Vide = même source que l'entrée.")
    source_locator = models.CharField("page / n° d'entrée", max_length=100, blank=True)
    text_key = models.TextField(blank=True, default="", editable=False)
    # Définition avec liens vers les autres mots du dictionnaire, calculée à l'enregistrement
    # (voir liens.py). Vide = pas encore calculée : on affiche alors le texte brut.
    text_html = models.TextField(blank=True, default="", editable=False)
    liens_version = models.CharField(max_length=20, blank=True, default="", editable=False)

    def save(self, *args, **kwargs):
        self.text_key = cle_recherche(self.text)
        self.text_html, self.liens_version = "", ""  # recalculés juste après (signal)
        super().save(*args, **kwargs)

    @property
    def rendu(self):
        """Définition prête à afficher : avec liens si calculée, sinon texte brut (échappé par le gabarit)."""
        from django.utils.safestring import mark_safe
        return mark_safe(self.text_html) if self.text_html else self.text

    class Meta(Orderable.Meta):
        verbose_name = "sens"

    @property
    def effective_source(self):
        return self.source or self.entry.source

    def __str__(self):
        return f"{self.entry_id} — {self.text[:40]}"


class PulaarEntryVariant(Orderable):
    """Autre forme du mot vedette (variante écrite, forme voisine) telle que la donne la source.
    Aucune étiquette de dialecte n'est supposée."""

    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="variants")
    form = models.CharField("forme", max_length=200)
    note = models.CharField("note", max_length=200, blank=True)
    search_key = models.CharField(max_length=220, blank=True, default="", db_index=True, editable=False)

    def save(self, *args, **kwargs):
        self.search_key = cle_recherche(self.form)
        super().save(*args, **kwargs)

    class Meta(Orderable.Meta):
        verbose_name = "forme variante"
        verbose_name_plural = "formes variantes"
        constraints = [models.UniqueConstraint(fields=["entry", "form"], name="uq_variant_entry_form")]

    def __str__(self):
        return self.form


class PulaarPronunciation(Orderable):
    """Prononciation écrite (alphabet phonétique international), éventuellement propre à une variété."""

    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="pronunciations")
    ipa = models.CharField("API (alphabet phonétique)", max_length=200, help_text="Ex. [ɗem.ŋal] — à saisir par un phonéticien.")
    dialect = models.ForeignKey(PulaarDialect, verbose_name="variété", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")
    note = models.CharField("note", max_length=200, blank=True)

    class Meta(Orderable.Meta):
        verbose_name = "prononciation"

    def __str__(self):
        return self.ipa


class PulaarAudio(Orderable):
    """Enregistrement de la prononciation. Public seulement avec le consentement du locuteur."""

    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="audios")
    audio = models.ForeignKey("wagtaildocs.Document", verbose_name="fichier audio", on_delete=models.CASCADE,
                              related_name="+", help_text="mp3, m4a, ogg ou wav, quelques secondes.")
    speaker = models.CharField("locuteur·rice", max_length=120, blank=True, help_text="Nom ou pseudonyme.")
    dialect = models.ForeignKey(PulaarDialect, verbose_name="variété", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")
    consent_given = models.BooleanField("consentement du locuteur obtenu", default=False,
                                        help_text="Sans cette case cochée, l'enregistrement reste invisible au public.")
    source = models.ForeignKey(PulaarSource, verbose_name="source", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="audios")

    class Meta(Orderable.Meta):
        verbose_name = "enregistrement audio"
        verbose_name_plural = "enregistrements audio"

    @property
    def public(self):
        return self.consent_given

    def __str__(self):
        return f"{self.entry_id} — {self.speaker or 'audio'}"


class PulaarImage(Orderable):
    """Illustration d'une entrée (un instrument, un objet…). Publique seulement si les droits sont vérifiés."""

    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="images")
    image = models.ForeignKey("wagtailimages.Image", verbose_name="image", on_delete=models.CASCADE, related_name="+")
    caption = models.CharField("légende", max_length=300, blank=True)
    credit = models.CharField("crédit (auteur, licence)", max_length=300, blank=True)
    rights_ok = models.BooleanField("droits de l'image vérifiés", default=False,
                                    help_text="Sans cette case cochée, l'image reste invisible au public.")
    source = models.ForeignKey(PulaarSource, verbose_name="source", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="images")

    class Meta(Orderable.Meta):
        verbose_name = "illustration"

    @property
    def public(self):
        return self.rights_ok

    def __str__(self):
        return self.caption or f"image {self.pk}"


class PulaarRelation(Orderable):
    """Lien d'une entrée vers une autre : synonyme, contraire, dérivé, pluriel…"""

    SYNONYME, CONTRAIRE, DERIVE, FAMILLE, PLURIEL, SINGULIER, VOIR = (
        "synonym", "antonym", "derived", "family", "plural", "singular", "see_also")
    TYPES = [(SYNONYME, "synonyme"), (CONTRAIRE, "contraire"), (DERIVE, "mot dérivé"),
             (FAMILLE, "même famille de mots"), (PLURIEL, "pluriel"), (SINGULIER, "singulier"),
             (VOIR, "voir aussi")]

    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="relations")
    kind = models.CharField("type de lien", max_length=12, choices=TYPES)
    target = models.ForeignKey(PulaarEntry, verbose_name="entrée liée", on_delete=models.CASCADE,
                               related_name="relations_entrantes")
    note = models.CharField("note", max_length=200, blank=True)

    class Meta(Orderable.Meta):
        verbose_name = "lien entre entrées"
        verbose_name_plural = "liens entre entrées"
        constraints = [models.UniqueConstraint(fields=["entry", "kind", "target"], name="uq_relation")]

    def clean(self):
        if self.target_id and self.target_id == self.entry_id:
            raise ValidationError("Une entrée ne peut pas être liée à elle-même.")

    def __str__(self):
        return f"{self.get_kind_display()} : {self.target_id}"


class PulaarExample(Orderable):
    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="examples")
    sense_number = models.PositiveSmallIntegerField("n° du sens illustré", null=True, blank=True)
    text = models.TextField("exemple en pulaar")
    translation = models.TextField("traduction (facultatif)", blank=True)
    source = models.ForeignKey(PulaarSource, verbose_name="source", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="examples")
    source_locator = models.CharField("page / n° d'entrée", max_length=100, blank=True)

    class Meta(Orderable.Meta):
        verbose_name = "exemple"

    def __str__(self):
        return self.text[:50]


class PulaarTranslation(Orderable):
    """Équivalent dans une autre langue. Ce n'est PAS une définition."""

    entry = ParentalKey(PulaarEntry, on_delete=models.CASCADE, related_name="translations")
    sense_number = models.PositiveSmallIntegerField("n° du sens (facultatif)", null=True, blank=True)
    language_code = models.CharField("langue (ISO 639-3)", max_length=3, validators=[CODE_ISO3],
                                     help_text="fra, eng, wol…")
    term = models.CharField("mot ou expression", max_length=300)
    external_dictionary = models.ForeignKey(PulaarExternalDictionary, verbose_name="dictionnaire externe",
                                            null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name="translations")
    source = models.ForeignKey(PulaarSource, verbose_name="source", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="translations")
    is_validated = models.BooleanField("vérifiée", default=False)

    class Meta(Orderable.Meta):
        verbose_name = "traduction"
        constraints = [models.UniqueConstraint(fields=["entry", "language_code", "term"],
                                               name="uq_translation_entry_lang_term")]

    @property
    def lien(self):
        if self.external_dictionary_id:
            return self.external_dictionary.url_for(self.term)
        return None

    def __str__(self):
        return f"{self.language_code}: {self.term}"


class PulaarProposal(models.Model):
    """Suggestion communautaire : jamais publiée directement, toujours passée
    par une file de relecture distincte du contenu final."""

    EN_ATTENTE, VALIDE, REJETE = "en_attente", "valide", "rejete"
    STATUTS = [(EN_ATTENTE, "En attente"), (VALIDE, "Validée"), (REJETE, "Rejetée")]

    term_lemma = models.CharField("mot proposé", max_length=200)
    definition_ff = models.TextField("définition en pulaar", blank=True)
    translation_fr = models.CharField("traduction en français (facultatif)", max_length=300, blank=True)
    dialect = models.ForeignKey(PulaarDialect, verbose_name="dialecte", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")
    pos = models.ForeignKey(PulaarPos, verbose_name="classe grammaticale", null=True, blank=True,
                            on_delete=models.SET_NULL, related_name="+",
                            help_text="À choisir par le relecteur avant de valider.")
    domain = models.ForeignKey(PulaarDomain, verbose_name="domaine", null=True, blank=True,
                               on_delete=models.SET_NULL)
    justification = models.TextField("d'où vient ce mot ?", blank=True)
    contributor_name = models.CharField("nom du contributeur", max_length=120, blank=True)
    contributor_contact = models.CharField("contact du contributeur", max_length=200, blank=True)
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+", editable=False)
    status = models.CharField("statut", max_length=20, choices=STATUTS, default=EN_ATTENTE)
    published_term = models.ForeignKey(PulaarEntry, null=True, blank=True, editable=False,
                                       on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "proposition"

    def __str__(self):
        return f"{self.term_lemma} ({self.get_status_display()})"

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Passer à « validée » publie l'entrée (une seule fois). Elle reste
        # « documentée », jamais « validée » : la validation linguistique est un
        # acte distinct.
        if self.status == self.VALIDE and self.published_term_id is None:
            self.published_term = self._publier()
            super().save(update_fields=["published_term"])

    def _publier(self):
        source, _ = PulaarSource.objects.get_or_create(
            method=SOURCE_COMMUNAUTE,
            defaults={"name": "Contribution communautaire", "license": "contribution relue par la rédaction",
                      "rights_status": PulaarSource.ACCORD,
                      "rights_note": "Le contributeur a proposé le mot via le formulaire public, en connaissance de sa publication."},
        )
        dialecte = self.dialect or PulaarDialect.objects.filter(code=DIALECTE_PAR_DEFAUT).first()
        pos = self.pos or PulaarPos.objects.filter(code="a-preciser").first()
        if dialecte is None or pos is None:
            raise ValidationError("Dialecte ou classe grammaticale introuvable : lancer seed_pulaar.")
        entree = PulaarEntry.objects.filter(lemma__iexact=self.term_lemma, dialect=dialecte, pos=pos).first()
        if entree is None:
            entree = PulaarEntry(lemma=self.term_lemma, dialect=dialecte, pos=pos, domain=self.domain,
                                 source=source,
                                 status=PulaarEntry.DOCUMENTE if self.definition_ff.strip() else PulaarEntry.BROUILLON)
            entree.save()
        if self.definition_ff.strip():
            PulaarSense.objects.create(entry=entree, text=self.definition_ff.strip(), source=source)
        if self.translation_fr.strip():
            PulaarTranslation.objects.get_or_create(
                entry=entree, language_code="fra", term=self.translation_fr.strip(), defaults={"source": source})
        return entree


def mot_du_jour(jour=None):
    """Une entrée du dictionnaire, la même toute la journée (rotation déterministe).
    Seules les entrées publiques ayant une définition EN PULAAR sont retenues :
    renvoie None s'il n'y en a pas."""
    from datetime import date

    jour = jour or date.today()
    qs = (PulaarEntry.objects.publiques().filter(senses__isnull=False).distinct()
          .select_related("source", "domain", "pos", "dialect").prefetch_related("senses").order_by("pk"))
    total = qs.count()
    if not total:
        return None
    entree = qs[jour.toordinal() % total]
    return {"terme": entree, "definition": entree.senses.first()}


class PulaarStopword(models.Model):
    """Mot qu'on ne transforme pas en lien dans les définitions (mots-outils, mots trop banals).

    Deux origines : « automatique » (mots présents plus de N fois dans les définitions : calculé par
    `hypertextualiser`, purement statistique, aucun jugement linguistique) et « manuel » (choisi par
    l'équipe). Une ligne manuelle l'emporte toujours : mode « exclure » = jamais de lien ; mode
    « lier » = garder le lien même si le mot est très fréquent ou très court."""

    EXCLURE, LIER = "exclude", "link"
    MODES = [(EXCLURE, "Ne pas lier"), (LIER, "Toujours lier")]
    AUTO, MANUEL = "auto", "manual"
    ORIGINES = [(AUTO, "Automatique (fréquence)"), (MANUEL, "Choisi par l'équipe")]

    forme = models.CharField("mot", max_length=80)
    cle = models.CharField(max_length=80, unique=True, editable=False)
    mode = models.CharField("effet", max_length=8, choices=MODES, default=EXCLURE)
    origine = models.CharField("origine", max_length=8, choices=ORIGINES, default=MANUEL)
    occurrences = models.PositiveIntegerField("occurrences dans les définitions", default=0, editable=False)
    note = models.CharField("note", max_length=200, blank=True)

    class Meta:
        ordering = ["-occurrences", "forme"]
        verbose_name = "mot sans lien"
        verbose_name_plural = "mots sans lien (mots-outils)"

    def save(self, *args, **kwargs):
        # Toute sauvegarde passe par une personne (le calcul automatique utilise bulk_create) :
        # la ligne devient « manuelle » et n'est plus jamais recalculée ni écrasée.
        self.cle = forme_exacte(self.forme)
        self.origine = self.MANUEL
        PulaarStopword.objects.filter(cle=self.cle, origine=self.AUTO).exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.forme


class PulaarMutation(models.Model):
    """Alternance de consonne initiale (ex. g ↔ w) utilisée pour retrouver un mot sous une autre forme.

    DÉSACTIVÉE par défaut et jamais pré-remplie : les paires doivent être fournies et validées par
    un lexicographe (IA ≠ autorité linguistique). Mesurer d'abord avec
    `manage.py hypertextualiser --rapport --paires g:w,...`."""

    initiale_a = models.CharField("initiale A", max_length=3)
    initiale_b = models.CharField("initiale B", max_length=3)
    actif = models.BooleanField("utiliser pour les liens", default=False)
    note = models.CharField("note / source de la règle", max_length=200, blank=True)

    class Meta:
        verbose_name = "alternance de consonne"
        verbose_name_plural = "alternances de consonnes"
        constraints = [models.UniqueConstraint(fields=["initiale_a", "initiale_b"], name="uq_mutation")]

    def __str__(self):
        return f"{self.initiale_a} ↔ {self.initiale_b}"
