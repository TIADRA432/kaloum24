"""Page d'import des lots dans l'administration Wagtail (réservée aux comptes autorisés)."""
import csv
import json

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .importer import ImportInvalide, importer, retirer_lot
from .models import PulaarEntry, PulaarImportBatch, PulaarPos

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
    "douteux": ("Lemme douteux (espace ou majuscule interne)", Q(lemma__contains=" ") | Q(lemma__regex=r".[A-ZƁƊƳŊÑ]")),
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
        "classes": PulaarPos.objects.all(),
    })


@permission_required("pulaar.change_pulaarentry", raise_exception=True)
@require_POST
def tableau_classe(request):
    """Change la classe grammaticale de plusieurs entrées d'un coup (file « classe à préciser »)."""
    ids = [int(i) for i in request.POST.getlist("ids") if i.isdigit()][:200]
    pos = PulaarPos.objects.filter(pk=request.POST.get("pos", "")).first() if request.POST.get("pos", "").isdigit() else None
    retour = reverse("pulaar_tableau")
    manque = request.POST.get("manque", "")
    if manque in MANQUES:
        retour += f"?manque={manque}&page={request.POST.get('page', '1') if request.POST.get('page', '1').isdigit() else 1}"
    if not ids or pos is None:
        messages.error(request, "Coche au moins un mot et choisis une classe.")
        return redirect(retour)
    modifiees, refusees = 0, []
    for e in PulaarEntry.objects.filter(pk__in=ids):
        try:
            with transaction.atomic():
                PulaarEntry.objects.filter(pk=e.pk).update(pos=pos)
            modifiees += 1
        except IntegrityError:  # même mot, même variété, même classe et même n° d'homonyme déjà présents
            refusees.append(e.lemma)
    if modifiees:
        messages.success(request, f"{modifiees} entrée(s) passée(s) en « {pos.name_fr} ».")
    if refusees:
        messages.warning(request, "Non modifiée(s), une entrée identique existe déjà : " + ", ".join(refusees[:10])
                         + ("…" if len(refusees) > 10 else "") + " — change leur numéro d'homonyme depuis la fiche.")
    return redirect(retour)


@permission_required("pulaar.change_pulaarentry", raise_exception=True)
def tableau_csv(request):
    """Exporte une file de travail en CSV (pour un relecteur hors ligne)."""
    manque = request.GET.get("manque", "")
    if manque not in MANQUES:
        return redirect(reverse("pulaar_tableau"))
    qs = (PulaarEntry.objects.filter(MANQUES[manque][1]).distinct()
          .select_related("dialect", "pos", "source").prefetch_related("senses").order_by("lemma", "homonym_index"))
    rep = HttpResponse(content_type="text/csv; charset=utf-8")
    rep["Content-Disposition"] = f'attachment; filename="dictionnaire-pulaar-{manque}.csv"'
    rep.write("\ufeff")  # BOM : Excel lit correctement l'UTF-8 (ɓ ɗ ŋ ƴ)
    w = csv.writer(rep)
    w.writerow(["id", "mot", "n_homonyme", "variete", "classe", "statut", "source", "definition"])
    for e in qs.iterator(chunk_size=500):
        sens = next(iter(e.senses.all()), None)
        w.writerow([e.pk, e.lemma, e.homonym_index, e.dialect.name, e.pos.name_fr, e.status,
                    e.source.name if e.source_id else "", (sens.text if sens else "")[:300]])
    return rep
