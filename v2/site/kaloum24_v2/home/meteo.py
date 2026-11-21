"""Météo Afrique de l'Ouest via Open-Meteo (sans clé).

Licence : gratuit pour un usage NON commercial, attribution CC BY 4.0 obligatoire
(« Météo : Open-Meteo.com »). Si le site vend de la publicité, passer à l'offre
commerciale d'Open-Meteo avant de garder ce service (voir PLAN_EVOLUTION §6, décision 2).

Un seul appel pour toutes les villes, mis en cache 3 h ; en cas de panne on réutilise
la dernière valeur connue (24 h) et, à défaut, on n'affiche rien : jamais d'erreur 500.
"""
import json
import logging
import urllib.parse
import urllib.request

from django.core.cache import cache

log = logging.getLogger(__name__)

VILLES = [  # nom, latitude, longitude
    ("Conakry", 9.5370, -13.6785),
    ("Labé", 11.3182, -12.2833),
    ("Kankan", 10.3854, -9.3057),
    ("Nzérékoré", 7.7562, -8.8179),
    ("Dakar", 14.6937, -17.4441),
    ("Bamako", 12.6392, -8.0029),
    ("Abidjan", 5.3600, -4.0083),
]
CLE, CLE_SECOURS = "meteo:v1", "meteo:v1:secours"
DUREE, DUREE_SECOURS = 3 * 3600, 24 * 3600
URL = "https://api.open-meteo.com/v1/forecast"

# Codes WMO → (libellé, symbole)
CODES = {0: ("Ciel dégagé", "☀️"), 1: ("Plutôt dégagé", "🌤️"), 2: ("Partiellement nuageux", "⛅"),
         3: ("Couvert", "☁️"), 45: ("Brouillard", "🌫️"), 48: ("Brouillard givrant", "🌫️"),
         51: ("Bruine légère", "🌦️"), 53: ("Bruine", "🌦️"), 55: ("Bruine forte", "🌦️"),
         61: ("Pluie faible", "🌧️"), 63: ("Pluie", "🌧️"), 65: ("Pluie forte", "🌧️"),
         80: ("Averses", "🌦️"), 81: ("Averses", "🌦️"), 82: ("Averses violentes", "⛈️"),
         95: ("Orage", "⛈️"), 96: ("Orage et grêle", "⛈️"), 99: ("Orage et grêle", "⛈️")}


def _decrire(code):
    return CODES.get(code, ("Variable", "🌡️"))


def _telecharger():
    params = urllib.parse.urlencode({
        "latitude": ",".join(str(v[1]) for v in VILLES),
        "longitude": ",".join(str(v[2]) for v in VILLES),
        "current": "temperature_2m,weather_code",
        "timezone": "GMT",
    })
    req = urllib.request.Request(f"{URL}?{params}", headers={"User-Agent": "Kaloum24/1.0"})
    with urllib.request.urlopen(req, timeout=2.5) as r:  # court : ne jamais bloquer une page
        data = json.loads(r.read().decode("utf-8"))
    if isinstance(data, dict):
        data = [data]
    villes = []
    for (nom, _, _), bloc in zip(VILLES, data):
        cur = bloc.get("current") or {}
        if cur.get("temperature_2m") is None:
            continue
        libelle, symbole = _decrire(cur.get("weather_code"))
        villes.append({"nom": nom, "temperature": round(cur["temperature_2m"]),
                       "libelle": libelle, "symbole": symbole})
    return villes


def meteo():
    """Liste de villes {nom, temperature, libelle, symbole}, ou [] si indisponible."""
    villes = cache.get(CLE)
    if villes is not None:
        return villes
    try:
        villes = _telecharger()
    except Exception as exc:  # réseau, quota, JSON…
        log.warning("Météo indisponible : %s", exc)
        villes = cache.get(CLE_SECOURS) or []
        cache.set(CLE, villes, 300)  # on réessaie dans 5 min, sans marteler l'API
        return villes
    if villes:
        cache.set(CLE, villes, DUREE)
        cache.set(CLE_SECOURS, villes, DUREE_SECOURS)
    return villes
