"""Recalcul des liens des définitions quand le dictionnaire change (après validation de la transaction)."""
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from . import liens
from .models import PulaarEntry, PulaarEntryVariant, PulaarSense, PulaarSource, PulaarStopword
from .slug import cle_recherche


def _plus_tard(fonction):
    if not liens.suspendu():
        transaction.on_commit(fonction)


def _relier(ids):
    ids = list(dict.fromkeys(ids))
    if ids:
        liens.relier_sens(ids)


@receiver(post_save, sender=PulaarSense)
def sens_enregistre(sender, instance, raw=False, **kw):
    if not raw:
        _plus_tard(lambda: _relier([instance.pk]))


@receiver(post_save, sender=PulaarEntry)
def entree_enregistree(sender, instance, raw=False, **kw):
    """Nouveau mot, mot renommé, mot publié/retiré : ses propres définitions, celles qui le citent
    et celles qui pointent déjà vers lui sont recalculées."""
    if raw:
        return

    def travail():
        cles = [instance.search_key] + [v.search_key for v in instance.variants.all()]
        propres = list(instance.senses.values_list("id", flat=True))
        _relier(propres + liens.sens_qui_mentionnent(cles) + liens.sens_qui_pointent_vers(instance.pk))
    _plus_tard(travail)


@receiver(post_delete, sender=PulaarEntry)
def entree_supprimee(sender, instance, **kw):
    pk = instance.pk  # Django remet instance.pk à None juste après : on le garde pour le recalcul différé
    _plus_tard(lambda: _relier(liens.sens_qui_pointent_vers(pk)))


@receiver(post_save, sender=PulaarEntryVariant)
@receiver(post_delete, sender=PulaarEntryVariant)
def variante_modifiee(sender, instance, **kw):
    cle, entree_id = cle_recherche(instance.form), instance.entry_id
    _plus_tard(lambda: _relier(liens.sens_qui_mentionnent([cle]) + liens.sens_qui_pointent_vers(entree_id)))


@receiver(pre_save, sender=PulaarSource)
def source_avant(sender, instance, **kw):
    ancien = PulaarSource.objects.filter(pk=instance.pk).values_list("rights_status", flat=True).first() if instance.pk else None
    instance._droits_changent = ancien is not None and ancien != instance.rights_status


@receiver(post_save, sender=PulaarSource)
def source_enregistree(sender, instance, **kw):
    """Les droits décident de ce qui est public, donc de qui peut pointer vers qui : tout est recalculé."""
    if getattr(instance, "_droits_changent", False):
        _plus_tard(lambda: liens.relier_sens(tous=True))


@receiver(post_save, sender=PulaarStopword)
@receiver(post_delete, sender=PulaarStopword)
def mot_outil_modifie(sender, instance, **kw):
    if instance.origine == PulaarStopword.MANUEL:
        _plus_tard(lambda: _relier(liens.sens_qui_mentionnent([cle_recherche(instance.forme)])))
