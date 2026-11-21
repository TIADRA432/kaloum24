from django.core.paginator import Paginator
from django.shortcuts import render

from . import presse
from .models import ArticlePresse, SourcePresse


def revue(request):
    presse.rafraichir_si_perime()
    qs = ArticlePresse.objects.filter(visible=True, source__actif=True).select_related("source")
    source = request.GET.get("source")
    if source and source.isdigit():
        qs = qs.filter(source_id=int(source))
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    sources = SourcePresse.objects.filter(actif=True)
    return render(request, "pages/revue_de_presse.html", {"page_obj": page, "sources": sources, "source_choisie": source})
