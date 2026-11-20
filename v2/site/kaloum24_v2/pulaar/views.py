from django.contrib import messages
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ProposalForm
from .models import PulaarDomain, PulaarProposal, PulaarTerm
from .slug import slugify_pulaar

PROPOSITIONS_PAR_HEURE = 5


def _langue(request):
    langue = request.GET.get("lang", "fr")
    return langue if langue in ("fr", "ff") else "fr"


def _ctx(request, **extra):
    return {"langue_ui": _langue(request), **extra}


def _termes():
    return PulaarTerm.objects.select_related("domain", "source").prefetch_related("definitions")


def accueil(request):
    q = request.GET.get("q", "").strip()[:100]
    resultats = []
    if q:
        # Beaucoup de claviers ne permettent pas de taper ɗ, ɓ, ŋ, ƴ : on
        # cherche TOUJOURS aussi dans le slug, forme translittérée du lemme.
        resultats = list(
            _termes().filter(
                Q(lemma__icontains=q)
                | Q(definitions__text__icontains=q)
                | Q(slug__icontains=slugify_pulaar(q))
            ).distinct()[:30]
        )
    total = PulaarTerm.objects.count()
    # Couverture monolingue affichée telle quelle, même à 0 : autant montrer
    # honnêtement la distance restante.
    monolingues = PulaarTerm.objects.filter(definitions__lang="ff").distinct().count()
    # Sans recherche on liste quand même les termes (page vide = visiteur perdu).
    tous = [] if q else list(_termes().order_by("lemma")[:100])
    return render(request, "pulaar/accueil.html", _ctx(
        request, q=q, resultats=resultats, domaines=PulaarDomain.objects.all(),
        total_termes=total, tous_termes=tous, termes_monolingues=monolingues,
    ))


def terme(request, slug):
    t = get_object_or_404(_termes(), slug=slug)
    return render(request, "pulaar/terme.html", _ctx(request, terme=t))


def domaine(request, slug):
    d = get_object_or_404(PulaarDomain, slug=slug)
    termes = _termes().filter(domain=d).order_by("lemma")
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
                definition_fr=d["definition_fr"].strip(),
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
