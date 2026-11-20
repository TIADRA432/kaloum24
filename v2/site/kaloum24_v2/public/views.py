from datetime import datetime, timezone

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.formats import date_format
from django.views.decorators.http import require_GET

CATEGORIES = (
    ("politique", "Politique"), ("economie", "Économie"), ("societe", "Société"),
    ("afrique", "Afrique"), ("culture", "Culture"), ("sport", "Sport"), ("pulaar", "Pulaar"),
)


@require_GET
def home(request):
    """Render the editorial shell honestly while no content has been imported."""
    query = request.GET.get("q", "").strip()[:200]
    category = request.GET.get("rubrique", "")
    labels = dict(CATEGORIES)
    now = datetime.now(timezone.utc)
    response = render(request, "kaloum24/home.html", {
        "categories": CATEGORIES,
        "selected_category": category if category in labels else "",
        "section_title": "Résultats de recherche" if query else labels.get(category, "À la une"),
        "query": query,
        "date_label": date_format(now, "l j F Y").capitalize(),
        "year": now.year,
    })
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def health(request):
    """Liveness only: a successful response makes no database-readiness claim."""
    response = JsonResponse({"status": "ok", "service": "kaloum24-v2"})
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def robots(request):
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain; charset=utf-8")
