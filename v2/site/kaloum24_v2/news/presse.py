"""Revue de presse : reprise licite de titres depuis des flux RSS publics.

Règles : titre + extrait de 400 caractères au plus + lien vers l'original + nom de la source.
Jamais le texte complet, jamais les images. Un User-Agent identifie le site ; une source qui
répond 403/erreur est simplement ignorée (on ne contourne pas un blocage). Un média peut demander
son retrait : décocher « actif » dans l'admin.
"""
import html
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone as dt_tz
from email.utils import parsedate_to_datetime

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.html import strip_tags

from .models import ArticlePresse, SourcePresse

log = logging.getLogger(__name__)
AGENT = "Mozilla/5.0 (compatible; Kaloum24-revue-de-presse/1.0; +https://kaloum24.onrender.com)"
EXTRAIT_MAX = 400
CONSERVER = 400  # nombre maximal de titres gardés en base
DELAI = 30 * 60  # secondes entre deux collectes (collecte « paresseuse » à la visite)
VERROU = "presse:verrou"

NS = {"dc": "http://purl.org/dc/elements/1.1/", "content": "http://purl.org/rss/1.0/modules/content/"}


def nettoyer(texte):
    t = html.unescape(strip_tags(texte or ""))
    t = re.sub(r"\s+", " ", t).strip()
    # supprime la phrase automatique « L'article ... est apparu en premier sur ... »
    t = re.sub(r"\s*(L['’]article|The post)\b.*?(est apparu en premier sur|appeared first on).*$", "", t, flags=re.I)
    t = re.sub(r"\s*(\[(…|\.\.\.)\])?\s*(The post|L['’]article|Cet article)\s.*$", "", t) if re.search(r"(The post|L['’]article|Cet article)\s", t) and len(t) > 120 else t
    return t


def couper(texte, maxi=EXTRAIT_MAX):
    if len(texte) <= maxi:
        return texte
    coupe = texte[: maxi - 1].rsplit(" ", 1)[0].rstrip(" ,;:.-—")
    return coupe + "…"


def lire_flux(contenu):
    """Retourne [(titre, extrait, lien, datetime)] depuis un flux RSS 2.0 (octets)."""
    texte = contenu.decode("utf-8", "replace") if isinstance(contenu, bytes) else contenu
    # certains flux (ex. Guinéenews) emploient des entités HTML (&eacute;) invalides en XML
    texte = re.sub(r"&([A-Za-z][A-Za-z0-9]*);",
                   lambda m: m.group(0) if m.group(1) in ("amp", "lt", "gt", "quot", "apos") else html.unescape(m.group(0)).replace("&", "&amp;"),
                   texte)
    racine = ET.fromstring(texte.encode("utf-8"))
    sortie = []
    for item in racine.iter("item"):
        titre = nettoyer(item.findtext("title"))
        lien = (item.findtext("link") or "").strip()
        if not titre or not lien.startswith(("http://", "https://")):
            continue
        extrait = couper(nettoyer(item.findtext("description")))
        brut = item.findtext("pubDate") or item.findtext("dc:date", namespaces=NS)
        try:
            quand = parsedate_to_datetime(brut)
            if quand.tzinfo is None:
                quand = quand.replace(tzinfo=dt_tz.utc)
        except (TypeError, ValueError):
            quand = timezone.now()
        sortie.append((titre[:300], extrait, lien[:600], quand))
    return sortie


def telecharger(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/rss+xml, application/xml, text/xml"})
    with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 (URL venant de l'admin)
        return r.read(3_000_000)


def collecter_source(source):
    """Retourne le nombre de nouveaux titres ; consigne l'erreur sans jamais lever."""
    try:
        entrees = lire_flux(telecharger(source.flux))
    except Exception as e:  # réseau, 403, XML invalide…
        source.derniere_erreur = f"{type(e).__name__}: {e}"[:240]
        source.save(update_fields=["derniere_erreur"])
        log.warning("Revue de presse: %s ignorée (%s)", source.nom, source.derniere_erreur)
        return 0
    nouveaux = 0
    for titre, extrait, lien, quand in entrees[:40]:
        _, cree = ArticlePresse.objects.get_or_create(
            lien=lien, defaults={"source": source, "titre": titre, "extrait": extrait, "publie_le": quand})
        nouveaux += cree
    source.derniere_collecte, source.derniere_erreur = timezone.now(), ""
    source.save(update_fields=["derniere_collecte", "derniere_erreur"])
    return nouveaux


def collecter():
    total = sum(collecter_source(s) for s in SourcePresse.objects.filter(actif=True))
    garder = list(ArticlePresse.objects.order_by("-publie_le").values_list("pk", flat=True)[:CONSERVER])
    if len(garder) == CONSERVER:
        ArticlePresse.objects.exclude(pk__in=garder).delete()
    return total


def rafraichir_si_perime():
    """À appeler à l'affichage : lance une collecte en arrière-plan si la dernière date de plus de 30 min."""
    if not getattr(settings, "REVUE_PRESSE_AUTO", True) or cache.get("presse:recent"):
        return
    if not cache.add(VERROU, 1, 300):  # une seule collecte à la fois
        return
    cache.set("presse:recent", 1, DELAI)
    import threading

    def travail():
        try:
            collecter()
        finally:
            cache.delete(VERROU)

    threading.Thread(target=travail, daemon=True).start()


def derniers(limite=12, par_source=3):
    """Titres récents, au plus `par_source` par média pour garder de la variété."""
    vus, sortie = {}, []
    for a in ArticlePresse.objects.filter(visible=True, source__actif=True).select_related("source")[:300]:
        if vus.get(a.source_id, 0) >= par_source:
            continue
        vus[a.source_id] = vus.get(a.source_id, 0) + 1
        sortie.append(a)
        if len(sortie) >= limite:
            break
    return sortie
