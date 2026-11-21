"""Météo Afrique de l'Ouest via l'API MET Norway (locationforecast 2.0, sans clé).

Pourquoi pas Open-Meteo : en production, l'IP partagée de Render reçoit « 429 Too Many
Requests ». MET Norway est gratuite, usage commercial compris, sous licence CC BY 4.0 et
NLOD : attribution obligatoire (« Météo : MET Norway ») et User-Agent identifiant le site.
Une requête par ville, en parallèle, mises en cache 3 h ; en cas de panne on réutilise la
dernière valeur connue (24 h) et, à défaut, on n'affiche rien : jamais d'erreur 500.
"""
import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache

log = logging.getLogger(__name__)

VILLES = [  # nom, latitude, longitude, pays : la Guinée d'abord, puis le monde peul d'ouest en est
    ("Conakry", 9.5370, -13.6785, "Guinée"),
    ("Labé", 11.3182, -12.2833, "Guinée"),
    ("Mamou", 10.3755, -12.0915, "Guinée"),
    ("Kankan", 10.3854, -9.3057, "Guinée"),
    ("Nzérékoré", 7.7562, -8.8179, "Guinée"),
    ("Saint-Louis", 16.0179, -16.4896, "Sénégal"),
    ("Dakar", 14.6937, -17.4441, "Sénégal"),
    ("Matam", 15.6559, -13.2554, "Sénégal"),
    ("Bamako", 12.6392, -8.0029, "Mali"),
    ("Mopti", 14.4843, -4.1830, "Mali"),
    ("Abidjan", 5.3600, -4.0083, "Côte d'Ivoire"),
    ("Accra", 5.6037, -0.1870, "Ghana"),
    ("Dori", 14.0354, -0.0346, "Burkina Faso"),
    ("Sokoto", 13.0059, 5.2476, "Nigéria"),
    ("Yola", 9.2035, 12.4954, "Nigéria"),
    ("Maroua", 10.5910, 14.3159, "Cameroun"),
    ("Ngaoundéré", 7.3167, 13.5833, "Cameroun"),
    ("Bambari", 5.7622, 20.6750, "Centrafrique"),
]
CLE, CLE_SECOURS = "meteo:v3", "meteo:v3:secours"
DUREE, DUREE_SECOURS = 3 * 3600, 24 * 3600
URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={:.4f}&lon={:.4f}"
AGENT = "Kaloum24/1.0 (+https://kaloum24.onrender.com)"

# Début du code de symbole MET → (libellé, symbole)
SYMBOLES = [("clearsky", "Ciel dégagé", "☀️"), ("fair", "Plutôt dégagé", "🌤️"),
            ("partlycloudy", "Partiellement nuageux", "⛅"), ("cloudy", "Couvert", "☁️"),
            ("fog", "Brouillard", "🌫️"), ("heavyrain", "Forte pluie", "🌧️"),
            ("lightrain", "Pluie faible", "🌦️"), ("rain", "Pluie", "🌧️"),
            ("heavysleet", "Pluie et neige", "🌧️"), ("sleet", "Pluie et neige", "🌧️"),
            ("snow", "Neige", "❄️"), ("lightssleet", "Pluie et neige", "🌧️")]


def _decrire(symbole):
    base = (symbole or "").split("_")[0]
    if "thunder" in base:
        return "Orage", "⛈️"
    if "showers" in base:
        return "Averses", "🌦️"
    for debut, libelle, icone in SYMBOLES:
        if base.startswith(debut):
            return libelle, icone
    return "Variable", "🌡️"


def _une_ville(ville):
    nom, lat, lon, pays = ville
    req = urllib.request.Request(URL.format(lat, lon), headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=3) as r:  # court : ne jamais bloquer une page
        data = json.loads(r.read().decode("utf-8"))
    premier = data["properties"]["timeseries"][0]["data"]
    temp = premier["instant"]["details"]["air_temperature"]
    resume = next((premier[k]["summary"]["symbol_code"] for k in ("next_1_hours", "next_6_hours", "next_12_hours")
                   if k in premier), "")
    libelle, icone = _decrire(resume)
    return {"nom": nom, "pays": pays, "temperature": round(temp), "libelle": libelle, "symbole": icone}


def _telecharger():
    def sur(ville):
        try:
            return _une_ville(ville)
        except Exception as exc:
            log.warning("Météo %s indisponible : %s", ville[0], exc)
            return None

    with ThreadPoolExecutor(max_workers=len(VILLES)) as pool:
        return [v for v in pool.map(sur, VILLES) if v]


def meteo():
    """Liste de villes {nom, temperature, libelle, symbole}, ou [] si indisponible."""
    villes = cache.get(CLE)
    if villes is not None:
        return villes
    villes = _telecharger()
    if villes:
        cache.set(CLE, villes, DUREE)
        cache.set(CLE_SECOURS, villes, DUREE_SECOURS)
        return villes
    villes = cache.get(CLE_SECOURS) or []
    cache.set(CLE, villes, 300)  # on réessaie dans 5 min, sans marteler l'API
    return villes
