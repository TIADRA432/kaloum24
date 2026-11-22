"""Page d'import des lots dans l'administration Wagtail (réservée aux comptes autorisés)."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
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
