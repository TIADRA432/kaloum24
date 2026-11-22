"""Page d'import des lots dans l'administration Wagtail (réservée aux comptes autorisés)."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .importer import ImportInvalide, importer, retirer_lot
from .models import PulaarEntry, PulaarImportBatch

TAILLE_MAX = 12 * 1024 * 1024


@permission_required("pulaar.add_pulaarimportbatch", raise_exception=True)
def import_lot(request):
    if request.method == "POST":
        fichier = request.FILES.get("fichier")
        ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        try:
            if fichier is None:
                raise ImportInvalide("Aucun fichier reçu.")
            if fichier.size > TAILLE_MAX:
                raise ImportInvalide("Fichier trop gros : envoyer les lots un par un (moins de 12 Mo).")
            brut = fichier.read()
            try:
                data = json.loads(brut.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                raise ImportInvalide("Ce fichier n'est pas un JSON UTF-8 valide.")
            lot = importer(data, brut, fichier.name, request.user)
            resume = (f"{fichier.name} : {lot.entries_created} entrée(s) créée(s), {lot.entries_skipped} déjà présente(s) "
                      f"ou ignorée(s), {lot.senses_created} sens, {lot.examples_created} exemple(s), "
                      f"{lot.variants_created} variante(s).")
            if ajax:
                return JsonResponse({"ok": True, "message": resume})
            messages.success(request, resume)
        except ImportInvalide as e:
            if ajax:
                return JsonResponse({"ok": False, "message": f"{getattr(fichier, 'name', '')} : {e}"}, status=400)
            messages.error(request, str(e))
        return redirect(reverse("pulaar_import"))
    lots = PulaarImportBatch.objects.select_related("source", "imported_by")[:50]
    return render(request, "pulaar/admin_import.html", {
        "lots": lots,
        "total_entrees": PulaarEntry.objects.count(),
        "page_title": "Importer un lot du dictionnaire",
    })


@permission_required("pulaar.delete_pulaarimportbatch", raise_exception=True)
@require_POST
def retirer(request, pk):
    try:
        lot = PulaarImportBatch.objects.get(pk=pk, status=PulaarImportBatch.FAIT)
    except PulaarImportBatch.DoesNotExist:
        messages.error(request, "Lot introuvable ou déjà retiré.")
    else:
        n = retirer_lot(lot)
        messages.success(request, f"Lot « {lot.file_name} » retiré : {n} élément(s) supprimé(s) (entrées, sens, exemples, variantes).")
    return redirect(reverse("pulaar_import"))


# ---------------------------------------------------------------- tableau de bord du travail ---
# Chaque filtre = « ce qu'il manque » : la file de travail des équipes.
MANQUES = {
    "validation": ("À valider par un lexicographe", Q(status=PulaarEntry.DOCUMENTE)),
    "classe": ("Classe grammaticale à préciser", Q(pos__code="a-preciser")),
    "classe_nominale": ("Sans classe nominale", Q(noun_class__isnull=True)),
    "ipa": ("Sans prononciation (API)", Q(pronunciations__isnull=True)),
    "audio": ("Sans enregistrement audio", Q(audios__isnull=True)),
    "image": ("Sans illustration", Q(images__isnull=True)),
    "origine": ("Sans origine ni étymologie", Q(origin="") & Q(etymology="")),
    "exemple": ("Sans exemple", Q(examples__isnull=True)),
    "traduction": ("Sans traduction", Q(translations__isnull=True)),
    "lien": ("Sans lien vers un autre mot", Q(relations__isnull=True) & Q(relations_entrantes__isnull=True)),
}


@permission_required("pulaar.change_pulaarentry", raise_exception=True)
def tableau(request):
    q = PulaarEntry.objects
    total = q.count()

    def n(cond):
        return q.filter(cond).distinct().count()

    couverture = [
        ("Entrées", total, None),
        ("avec une définition en pulaar", n(Q(senses__isnull=False)), total),
        ("validées par un lexicographe", n(Q(status=PulaarEntry.VALIDE)), total),
        ("avec une classe nominale", n(Q(noun_class__isnull=False)), total),
        ("avec une prononciation (API)", n(Q(pronunciations__isnull=False)), total),
        ("avec un enregistrement audio", n(Q(audios__isnull=False)), total),
        ("avec une illustration", n(Q(images__isnull=False)), total),
        ("avec une origine ou une étymologie", n(~Q(origin="") | ~Q(etymology="")), total),
        ("avec un exemple", n(Q(examples__isnull=False)), total),
        ("avec un lien vers un autre mot", n(Q(relations__isnull=False) | Q(relations_entrantes__isnull=False)), total),
        ("visibles du public", q.publiques().count(), total),
    ]
    couverture = [(lib, v, t, round(100 * v / t) if t else 0) for lib, v, t in couverture]
    par_dialecte = (q.values("dialect__name").annotate(n=Count("id")).order_by("-n"))
    par_source = (q.values("source__name", "source__rights_status").annotate(n=Count("id")).order_by("-n"))
    manque = request.GET.get("manque", "")
    page = liste = None
    if manque in MANQUES:
        qs = q.filter(MANQUES[manque][1]).distinct().select_related("dialect", "pos").order_by("lemma", "homonym_index")
        page = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, "pulaar/admin_tableau.html", {
        "couverture": couverture, "par_dialecte": par_dialecte, "par_source": par_source,
        "manques": [(k, v[0]) for k, v in MANQUES.items()], "manque": manque,
        "manque_libelle": MANQUES[manque][0] if manque in MANQUES else "", "page": page,
    })
