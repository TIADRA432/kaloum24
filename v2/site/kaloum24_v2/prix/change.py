"""Cours de référence de la BCRG (Banque Centrale de la République de Guinée), en GNF.

La BCRG publie chaque jour ouvré un PDF « Cours de référence des principales devises contre GNF »,
annoncé par une entrée de son site WordPress (API publique). On lit l'adresse du dernier PDF, on en
extrait le texte et on enregistre les cours. Rien n'est inventé : sans PDF lisible, on garde le dernier
cours connu avec sa date. Seules les adresses du site de la BCRG sont suivies.
"""
import io
import json
import logging
import re
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.cache import cache

from .models import TauxChange

log = logging.getLogger(__name__)

API = "https://www.bcrg-guinee.org/wp-json/wp/v2/cours_des_devises?per_page=1"
PREFIXE_PDF = "https://www.bcrg-guinee.org/wp-content/uploads/"
AGENT = {"User-Agent": "Kaloum24/1.0 (+https://kaloum24.onrender.com)"}
DEVISES = {"USD": "Dollar des États-Unis", "EUR": "Euro", "XOF": "Franc CFA (XOF et XAF)", "GBP": "Livre sterling",
           "CHF": "Franc suisse", "CAD": "Dollar canadien", "CNY": "Yuan chinois", "JPY": "Yen japonais",
           "SAR": "Riyal saoudien", "DKK": "Couronne danoise", "NOK": "Couronne norvégienne", "SEK": "Couronne suédoise"}
RE_DATE = re.compile(r"CONTRE\s+GNF\s+AU\s+(\d{2})/(\d{2})/(\d{4})", re.I)
RE_CODE = re.compile(r"(?<![A-Za-z])([A-Z]{3})(?![A-Za-z])")
ESPACES = "\u00a0\u202f "
RE_NOMBRE = re.compile(r"(?:\d{1,3}(?:[" + ESPACES + r"]\d{3})+|\d+)(?:[.,]\d+)?")
FCFA_PAR_EURO = Decimal("655.957")  # parité fixe légale XOF/XAF–EUR


def lire_pdf(octets):
    """Texte d'un PDF de cours (couche texte). Lève une exception si illisible."""
    from pypdf import PdfReader

    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(octets)).pages)


def analyser(texte):
    """(date, {code: cours}) à partir du texte du PDF ; (None, {}) si le format n'est pas reconnu."""
    m = RE_DATE.search(texte)
    if not m:
        return None, {}
    jour = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    cours = {}
    for ligne in texte.splitlines():  # « USD   8839,01 » ou « 8839.0137USD » selon le lecteur de PDF
        codes = [c for c in RE_CODE.findall(ligne) if c in DEVISES]
        nombres = RE_NOMBRE.findall(ligne)
        if len(codes) != 1 or not nombres:
            continue
        valeur = "".join(ch for ch in nombres[-1] if ch not in ESPACES).replace(",", ".")
        try:
            d = Decimal(valeur)
        except InvalidOperation:
            continue
        if d > 0:
            cours[codes[0]] = d
    return jour, cours


def _get(url, limite):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=20) as r:  # noqa: S310
        return r.read(limite)


def url_dernier_pdf():
    entrees = json.loads(_get(API, 500_000))
    corps = entrees[0]["content"]["rendered"] if entrees else ""
    m = re.search(r"https:(?:\\{0,2}/){2}www\.bcrg-guinee\.org[^\"'<>\s]+?\.pdf", corps)
    url = m.group(0).replace("\\", "") if m else ""
    return url if url.startswith(PREFIXE_PDF) else ""


def importer():
    """Lit le dernier PDF de la BCRG et enregistre ses cours. Retourne le nombre de cours ajoutés."""
    url = url_dernier_pdf()
    if not url:
        return 0
    jour, cours = analyser(lire_pdf(_get(url, 3_000_000)))
    if not jour or "USD" not in cours or "EUR" not in cours:  # format inattendu : on n'enregistre rien
        log.warning("BCRG : PDF non reconnu (%s)", url)
        return 0
    n = 0
    for code, valeur in cours.items():
        _, cree = TauxChange.objects.get_or_create(date=jour, devise=code, defaults={"cours": valeur, "source_url": url})
        n += cree
    return n


def rafraichir_si_perime():
    """À l'affichage : une tentative par heure au plus, en arrière-plan, tant que le cours du jour manque."""
    from django.conf import settings

    if not getattr(settings, "REVUE_PRESSE_AUTO", True) or cache.get("change:recent"):
        return
    cache.set("change:recent", 1, 3600)
    dernier = TauxChange.objects.values_list("date", flat=True).first()
    if dernier == date.today():
        return
    import threading

    def travail():
        try:
            importer()
        except Exception as exc:  # réseau, PDF changé…
            log.warning("BCRG indisponible : %s", exc)

    threading.Thread(target=travail, daemon=True).start()


def derniers_cours():
    """(date, {code: Decimal}, source_url) du cours le plus récent, ou (None, {}, "")."""
    jour = TauxChange.objects.values_list("date", flat=True).first()
    if not jour:
        return None, {}, ""
    lignes = list(TauxChange.objects.filter(date=jour))
    return jour, {t.devise: t.cours for t in lignes}, lignes[0].source_url


def convertir(montant, de, vers, cours):
    """Montant converti via le GNF ; None si une devise est inconnue."""
    cours = {**cours, "GNF": Decimal(1)}
    if de not in cours or vers not in cours:
        return None
    return montant * cours[de] / cours[vers]
