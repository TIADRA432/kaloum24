"""Calculs des prix affichés. Médiane des marchés (jamais la moyenne) ; aucune valeur sans effectif affiché."""
from statistics import median

from .models import Observation


def mois_recent(produit):
    o = Observation.objects.filter(produit=produit).order_by("-date").first()
    return o.date if o else None


def serie_nationale(produit, nb_mois=24):
    """[(date, médiane, nb_marchés)] par mois, du plus ancien au plus récent."""
    par_mois = {}
    for d, p in Observation.objects.filter(produit=produit).values_list("date", "prix"):
        par_mois.setdefault(d, []).append(float(p))
    mois = sorted(par_mois)[-nb_mois:]
    return [(m, median(par_mois[m]), len(par_mois[m])) for m in mois]


def resume(produit):
    """Dernier prix médian, effectif, variation sur 1 et 12 mois (en %), ou None si pas de données."""
    s = serie_nationale(produit, 24)
    if not s:
        return None
    dernier = s[-1]
    d = dict(date=dernier[0], prix=dernier[1], marches=dernier[2], serie=s, v1=None, v12=None)
    index = {m: p for m, p, _ in s}
    for cle, decalage in (("v1", 1), ("v12", 12)):
        mois_ref = _moins_mois(dernier[0], decalage)
        ref = index.get(mois_ref)
        if ref:
            d[cle] = round((dernier[1] - ref) / ref * 100, 1)
    return d


def _moins_mois(d, n):
    a, m = divmod(d.year * 12 + d.month - 1 - n, 12)
    return d.replace(year=a, month=m + 1, day=d.day)


def par_marche(produit):
    """Dernier relevé de chaque marché pour le mois le plus récent."""
    mois = mois_recent(produit)
    if not mois:
        return []
    return list(Observation.objects.filter(produit=produit, date=mois).select_related("lieu").order_by("prix"))


def courbe_svg(serie, largeur=640, hauteur=200):
    """Courbe SVG légère (aucun JavaScript). `serie` = [(date, valeur, n)]."""
    if len(serie) < 2:
        return ""
    vals = [v for _, v, _ in serie]
    lo, hi = min(vals), max(vals)
    marge = 14
    ecart = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        x = marge + i * (largeur - 2 * marge) / (len(vals) - 1)
        y = hauteur - marge - (v - lo) / ecart * (hauteur - 2 * marge)
        pts.append(f"{x:.1f},{y:.1f}")
    return (f'<svg viewBox="0 0 {largeur} {hauteur}" role="img" aria-label="Courbe du prix sur {len(serie)} mois" class="px-courbe">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="5" fill="currentColor"/></svg>')
