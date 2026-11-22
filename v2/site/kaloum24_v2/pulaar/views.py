from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Q
from django.db.models.functions import Substr, Upper
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from urllib.parse import urlencode
from django.views.decorators.http import require_http_methods

from .forms import ProposalForm
from .models import PulaarDialect, PulaarDomain, PulaarEntry, PulaarPos, PulaarProposal
from .recherche import RAISONS, chercher
from .slug import cle_recherche, slugify_pulaar

PROPOSITIONS_PAR_HEURE = 5
PAR_PAGE = 100
RESULTATS_PAR_PAGE = 30


def _apercu(request):
    """Vrai si l'équipe connectée voit des entrées que le public ne voit pas."""
    u = request.user
    return bool(u.is_authenticated and u.is_staff)


def _langue(request):
    langue = request.GET.get("lang", "fr")
    return langue if langue in ("fr", "ff") else "fr"


def _ctx(request, **extra):
    return {"langue_ui": _langue(request), **extra}


def _termes(request=None):
    """Entrées visibles : le public ne voit ni brouillon ni source aux droits non établis ;
    un compte d'équipe connecté voit tout (aperçu avant publication, bandeau « non public »)."""
    qs = PulaarEntry.objects.visibles_pour(getattr(request, "user", None))
    return (qs
            .select_related("domain", "source", "dialect", "pos")
            .prefetch_related("senses", "variants", "translations__external_dictionary"))


def _lettres(base):
    """Initiales présentes (A, B, Ɓ, C…), dans l'ordre alphabétique."""
    initiales = set(base.order_by().annotate(i=Upper(Substr("lemma", 1, 1))).values_list("i", flat=True).distinct())
    initiales.discard("")
    return sorted(initiales, key=lambda c: (cle_recherche(c) or c, c))


def _qs(request, **sauf):
    """Paramètres de la requête à conserver dans les liens (sans « page »)."""
    pr = {k: v for k, v in request.GET.items() if v and k != "page"}
    pr.update({k: v for k, v in sauf.items() if v})
    return urlencode(pr)


def accueil(request):
    q = request.GET.get("q", "").strip()[:100]
    code_dialecte = request.GET.get("dialecte", "").strip()[:10]
    code_classe = request.GET.get("classe", "").strip()[:30]
    lettre = request.GET.get("lettre", "").strip()[:2]
    base = _termes(request)
    if code_dialecte:
        base = base.filter(dialect__code=code_dialecte)
    if code_classe:
        base = base.filter(pos__code=code_classe)
    total = base.count()
    monolingues = base.filter(senses__isnull=False).distinct().count()
    lettres = _lettres(base)
    page = None
    resultats, nb_resultats = [], 0
    if q:
        # Résultats classés (mot exact d'abord), paginés, avec la raison du résultat.
        trouves = chercher(base, q)
        nb_resultats = len(trouves)
        page = Paginator(trouves, RESULTATS_PAR_PAGE).get_page(request.GET.get("page"))
        rangs = dict(page.object_list)
        par_id = {e.pk: e for e in base.filter(pk__in=rangs)}
        for pk, rang in page.object_list:
            e = par_id.get(pk)
            if e:
                e.raison = RAISONS[rang]
                resultats.append(e)
    else:
        liste = base.filter(lemma__istartswith=lettre) if lettre else base
        page = Paginator(liste.order_by("lemma", "homonym_index"), PAR_PAGE).get_page(request.GET.get("page"))
        resultats = list(page)
        nb_resultats = page.paginator.count
    return render(request, "pulaar/accueil.html", _ctx(
        request, q=q, resultats=resultats, domaines=PulaarDomain.objects.all(),
        dialectes=PulaarDialect.objects.filter(entries__isnull=False).distinct(), dialecte=code_dialecte,
        classes=PulaarPos.objects.filter(entries__isnull=False).distinct(), classe=code_classe,
        lettres=lettres, lettre=lettre, nb_resultats=nb_resultats,
        total_termes=total, termes_monolingues=monolingues, page=page,
        qs=_qs(request), qs_lettre=_qs(request, lettre=""),
        apercu_equipe=_apercu(request),
    ))


def terme(request, slug):
    t = get_object_or_404(_termes(request), slug=slug)
    traductions = {}
    for tr in t.translations.all():
        traductions.setdefault(tr.language_code, []).append(tr)
    non_public = not (t.status != t.BROUILLON and t.source.is_publishable)
    return render(request, "pulaar/terme.html", _ctx(request, terme=t, traductions=traductions, non_public=non_public))


def domaine(request, slug):
    d = get_object_or_404(PulaarDomain, slug=slug)
    termes = _termes(request).filter(domain=d).order_by("lemma")
    return render(request, "pulaar/domaine.html", _ctx(request, domaine=d, termes=termes))


def _ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0].strip()


@require_http_methods(["GET", "POST"])
def proposer(request):
    form = ProposalForm(request.POST or None)
    if request.method == "POST":
        if request.POST.get("site_web"):  # robot : on fait semblant de réussir
            return redirect(reverse("pulaar:accueil"))
        cle = f"pulaar-prop-{_ip(request)}"
        if cache.get(cle, 0) >= PROPOSITIONS_PAR_HEURE:
            messages.error(request, "Trop de propositions en peu de temps. Réessaie dans une heure.")
        elif form.is_valid():
            d = form.cleaned_data
            PulaarProposal.objects.create(
                term_lemma=d["term_lemma"].strip(),
                definition_ff=d["definition_ff"].strip(),
                translation_fr=d["translation_fr"].strip(),
                dialect=d["dialect"],
                domain=d["domain"],
                justification=d["justification"].strip(),
                contributor_name=d["contributor_name"].strip(),
                contributor_contact=d["contributor_contact"].strip(),
                proposed_by=request.user if request.user.is_authenticated else None,
            )
            cache.set(cle, cache.get(cle, 0) + 1, 3600)
            messages.success(request, "Merci — ta proposition part en relecture avant toute publication.")
            return redirect(reverse("pulaar:accueil"))
    return render(request, "pulaar/proposer.html", _ctx(request, form=form))
