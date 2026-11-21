from django.db import models


class Produit(models.Model):
    """Produit suivi. `code` = nom exact dans le jeu de données d'origine (clé d'import)."""

    code = models.CharField("code d'origine", max_length=80, unique=True)
    nom = models.CharField("nom", max_length=80)
    unite = models.CharField("unité", max_length=20, help_text="kg, litre, pièce…")
    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=100)
    a_la_une = models.BooleanField("sur l'accueil", default=False)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "produit"

    def __str__(self):
        return self.nom


class Lieu(models.Model):
    nom = models.CharField("marché", max_length=120, unique=True)
    region = models.CharField("région", max_length=80, blank=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "marché"
        verbose_name_plural = "marchés"

    def __str__(self):
        return self.nom


class Observation(models.Model):
    """Un prix relevé : un produit, un marché, un mois. Toujours rattaché à sa source."""

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="observations")
    lieu = models.ForeignKey(Lieu, on_delete=models.CASCADE, related_name="observations")
    date = models.DateField("mois du relevé")
    prix = models.DecimalField("prix (GNF)", max_digits=12, decimal_places=2)
    source = models.CharField("source", max_length=160, default="Programme alimentaire mondial (PAM), via HDX — CC BY-IGO")

    class Meta:
        ordering = ["-date"]
        verbose_name = "relevé de prix"
        verbose_name_plural = "relevés de prix"
        constraints = [models.UniqueConstraint(fields=["produit", "lieu", "date"], name="prix_unique_releve")]
        indexes = [models.Index(fields=["produit", "-date"])]

    def __str__(self):
        return f"{self.produit} · {self.lieu} · {self.date:%m/%Y}: {self.prix} GNF"


class TauxChange(models.Model):
    """Cours de référence de la BCRG : combien de GNF pour 1 unité de la devise, à une date donnée."""

    date = models.DateField("date du cours")
    devise = models.CharField("code devise", max_length=5, help_text="USD, EUR, XOF…")
    cours = models.DecimalField("GNF pour 1 unité", max_digits=14, decimal_places=4)
    source_url = models.URLField("document source", max_length=300, blank=True)

    class Meta:
        ordering = ["-date", "devise"]
        unique_together = [("date", "devise")]
        verbose_name = "cours de change (BCRG)"
        verbose_name_plural = "cours de change (BCRG)"

    def __str__(self):
        return f"{self.devise} {self.date} : {self.cours}"
