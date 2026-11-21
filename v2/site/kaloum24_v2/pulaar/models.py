from django.conf import settings
from django.db import models, transaction
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.models import Orderable

from .slug import slug_unique

SOURCE_COMMUNAUTE = "communaute"


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


class PulaarSource(models.Model):
    """Provenance d'un terme. Jamais de donnée sans source rattachée."""

    name = models.CharField("nom", max_length=200)
    url = models.URLField("lien", max_length=500, blank=True)
    license = models.CharField("licence", max_length=100, blank=True)
    method = models.CharField("méthode", max_length=30, help_text="wiktionary, import_manuel, communaute…")

    class Meta:
        ordering = ["name"]
        verbose_name = "source"

    def __str__(self):
        return self.name


class PulaarTerm(ClusterableModel):
    """Un terme du dictionnaire.

    « documenté » = vient d'une source ou d'une proposition acceptée, sans
    vérification linguistique supplémentaire ; « validé » = un lexicographe l'a
    explicitement confirmé. Jamais présumé validé.
    """

    DOCUMENTE, VALIDE = "documented", "validated"
    STATUTS = [(DOCUMENTE, "Documenté"), (VALIDE, "Validé")]

    lemma = models.CharField("mot (lemme)", max_length=200)
    slug = models.SlugField(max_length=220, unique=True, editable=False)
    part_of_speech = models.CharField("classe grammaticale", max_length=50, blank=True)
    status = models.CharField("statut", max_length=20, choices=STATUTS, default=DOCUMENTE)
    domain = models.ForeignKey(PulaarDomain, verbose_name="domaine", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="terms")
    # PROTECT volontaire : supprimer une source qui a encore des termes doit
    # être bloqué, pas transformé en donnée orpheline.
    source = models.ForeignKey(PulaarSource, verbose_name="source", on_delete=models.PROTECT,
                               related_name="terms")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["lemma"]
        verbose_name = "terme"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unique(PulaarTerm, self.lemma, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.lemma


class PulaarDefinition(Orderable):
    LANGUES = [("ff", "Pulaar"), ("fr", "Français"), ("en", "English")]

    term = ParentalKey(PulaarTerm, on_delete=models.CASCADE, related_name="definitions")
    lang = models.CharField("langue", max_length=5, choices=LANGUES)
    text = models.TextField("définition")

    def __str__(self):
        return f"{self.lang} — {self.term_id}"


class PulaarProposal(models.Model):
    """Suggestion communautaire : jamais publiée directement, toujours passée
    par une file de modération distincte du contenu final."""

    EN_ATTENTE, VALIDE, REJETE = "en_attente", "valide", "rejete"
    STATUTS = [(EN_ATTENTE, "En attente"), (VALIDE, "Validée"), (REJETE, "Rejetée")]

    term_lemma = models.CharField("mot proposé", max_length=200)
    # Les deux définitions sont facultatives en base ; la vue exige qu'au moins
    # une des deux soit fournie : un locuteur doit pouvoir contribuer en pulaar
    # seul, sans passer par le français.
    definition_ff = models.TextField("définition en pulaar", blank=True)
    definition_fr = models.TextField("définition en français", blank=True)
    domain = models.ForeignKey(PulaarDomain, verbose_name="domaine", null=True, blank=True,
                               on_delete=models.SET_NULL)
    justification = models.TextField("d'où vient ce mot ?", blank=True)
    contributor_name = models.CharField("nom du contributeur", max_length=120, blank=True)
    contributor_contact = models.CharField("contact du contributeur", max_length=200, blank=True)
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+", editable=False)
    status = models.CharField("statut", max_length=20, choices=STATUTS, default=EN_ATTENTE)
    published_term = models.ForeignKey(PulaarTerm, null=True, blank=True, editable=False,
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
        # Passer à « validée » publie le terme (une seule fois). Le terme reste
        # « documenté », jamais « validé » : la validation linguistique est un
        # acte distinct.
        if self.status == self.VALIDE and self.published_term_id is None:
            self.published_term = self._publier()
            super().save(update_fields=["published_term"])

    def _publier(self):
        source, _ = PulaarSource.objects.get_or_create(
            method=SOURCE_COMMUNAUTE,
            defaults={"name": "Contribution communautaire", "license": "contribution relue par la rédaction"},
        )
        terme = PulaarTerm.objects.filter(lemma__iexact=self.term_lemma).first()
        if terme is None:
            terme = PulaarTerm(lemma=self.term_lemma, domain=self.domain, source=source)
            terme.save()
        for langue, texte in (("ff", self.definition_ff), ("fr", self.definition_fr)):
            if texte.strip():
                PulaarDefinition.objects.create(term=terme, lang=langue, text=texte.strip())
        return terme


def mot_du_jour(jour=None):
    """Un terme du dictionnaire, le même toute la journée (rotation déterministe).
    Donnée réelle et sourcée : renvoie None si le dictionnaire est vide."""
    from datetime import date

    jour = jour or date.today()
    total = PulaarTerm.objects.count()
    if not total:
        return None
    terme = (PulaarTerm.objects.select_related("source", "domain")
             .prefetch_related("definitions").order_by("pk")[jour.toordinal() % total])
    definition = next((d for d in terme.definitions.all() if d.lang == "fr"), None) or next(
        iter(terme.definitions.all()), None)
    return {"terme": terme, "definition": definition}
