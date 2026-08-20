"""Lecture des flux RSS/Atom des sources externes.

Isolé dans son propre module (comme whatsapp_client.py) pour que les tests
puissent remplacer fetch_feed par une fonction factice, sans appel réseau
réel ni dépendance à la disponibilité des sites tiers.

Retourne toujours titre, extrait, lien, image, auteur, date — et, quand le
flux le fournit, le contenu intégral (`content_full`). Ce dernier n'est
utilisé que pour une source explicitement classée gouvernementale ou
institutionnelle, avec justification écrite enregistrée (voir
Source.content_mode dans models.py) ; pour toute autre source, il reste
extrait à l'admin par collector.py avant enregistrement. Voir
PLAN_AGREGATEUR.md, §0, sur la raison de cette distinction.
"""
import re
import socket
from datetime import datetime, timezone

import feedparser

from utils import sanitize_html, strip_html

TIMEOUT_SECONDES = 10
USER_AGENT = "Kaloum24Bot/1.0 (+agrégateur d'actualités ; contact via le site)"
MAX_EXTRAIT = 400          # au-delà, on tronque : un extrait n'est pas l'article
LIMITE_ITEMS = 30           # un flux mal configuré ne doit pas noyer la collecte


class ErreurFlux(Exception):
    """Le flux n'a pas pu être lu ou compris."""


def robots_autorise(feed_url):
    """Vérifie en direct que robots.txt n'interdit pas l'accès à ce flux.

    Revérifié à CHAQUE collecte plutôt qu'une seule fois à l'activation de la
    source (voir seed_sources.py) : un site peut modifier son robots.txt
    après coup, et la conformité vérifiée par l'admin à l'activation ne
    protège pas contre un changement ultérieur.

    Retourne (autorise, crawl_delay). Si robots.txt est injoignable (panne,
    timeout), on n'interprète PAS ça comme une interdiction — seul un refus
    explicite bloque la collecte.
    """
    from urllib.parse import urlparse
    from urllib.robotparser import RobotFileParser
    import urllib.request

    parsed = urlparse(feed_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        r = urllib.request.urlopen(req, timeout=TIMEOUT_SECONDES)
        contenu = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return True, None

    rp = RobotFileParser()
    rp.parse(contenu.splitlines())
    agent = USER_AGENT.split("/")[0]
    autorise = rp.can_fetch(agent, feed_url) and rp.can_fetch("*", feed_url)
    delay = rp.crawl_delay("*") or rp.crawl_delay(agent)
    return autorise, delay


def fetch_feed(feed_url):
    """Lit un flux RSS/Atom et retourne une liste d'items normalisés.

    Chaque item : {url, title, excerpt, image_url, author, published_at}.
    Lève ErreurFlux en cas d'échec — à charge de l'appelant de décider quoi
    en faire (marquer la source en erreur, continuer avec les autres, etc.).
    """
    ancien_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(TIMEOUT_SECONDES)
    try:
        analyse = feedparser.parse(feed_url, agent=USER_AGENT)
    except Exception as exc:
        raise ErreurFlux(f"Impossible de lire le flux : {exc}") from exc
    finally:
        socket.setdefaulttimeout(ancien_timeout)

    # feedparser ne lève pas toujours d'exception sur une erreur HTTP — il
    # faut vérifier `bozo` (flux malformé) et le statut quand il est présent.
    statut = getattr(analyse, "status", None)
    if statut and statut >= 400:
        raise ErreurFlux(f"Le serveur a répondu {statut}.")
    if analyse.bozo and not analyse.entries:
        detail = str(analyse.get("bozo_exception", "format non reconnu"))
        raise ErreurFlux(f"Flux illisible : {detail}")

    items = []
    for entree in analyse.entries[:LIMITE_ITEMS]:
        url = entree.get("link")
        titre = entree.get("title")
        if not url or not titre:
            continue          # item sans lien ou sans titre : inutilisable

        items.append({
            "url": url,
            "title": titre.strip(),
            "excerpt": _extraire_resume(entree),
            "content_full": _extraire_contenu_integral(entree),
            "image_url": _extraire_image(entree),
            "author": entree.get("author"),
            "published_at": _extraire_date(entree),
        })

    return items


def _extraire_contenu_integral(entree):
    """Le contenu intégral d'un item, quand le flux le fournit — le champ
    RSS `content:encoded` ou Atom `content`, que feedparser normalise en
    `entry.content` (distinct de `summary`, qui reste un extrait court).

    Assaini ici, à l'extraction — pas laissé à la charge du code appelant,
    même si ce contenu ne sert que pour une source explicitement classée
    gouvernementale/institutionnelle (voir Source.content_mode). Un HTML
    non fiable reste un HTML non fiable, quelle que soit la confiance
    accordée à la source qui l'a publié.

    Retourne None si le flux ne fournit rien de plus que le résumé déjà
    capté par _extraire_resume — pas la peine de dupliquer.
    """
    blocs = entree.get("content")
    if not blocs:
        return None

    brut = blocs[0].get("value", "")
    if not brut or not brut.strip():
        return None

    return sanitize_html(brut)


def _extraire_resume(entree):
    brut = entree.get("summary") or entree.get("description") or ""
    # Les flux RSS mettent parfois du HTML dans le résumé — on ne le rend
    # jamais tel quel (voir utils.strip_html).
    texte = strip_html(brut)
    if len(texte) > MAX_EXTRAIT:
        texte = texte[:MAX_EXTRAIT].rsplit(" ", 1)[0] + "…"
    return texte or None


def _extraire_image(entree):
    # Ordre de priorité : media_content/media_thumbnail (Media RSS), puis
    # enclosure (podcast/RSS classique), puis — le cas le plus fréquent en
    # pratique sur les flux WordPress — une balise <img> directement dans le
    # HTML du résumé (l'image « à la une » y est insérée par la plupart des
    # thèmes, faute d'un champ RSS dédié).
    for bloc in (entree.get("media_content") or []) + (entree.get("media_thumbnail") or []):
        if bloc.get("url"):
            return bloc["url"]
    for pj in entree.get("links", []) or []:
        if str(pj.get("type", "")).startswith("image/") and pj.get("href"):
            return pj["href"]
    for pj in entree.get("enclosures", []) or []:
        if str(pj.get("type", "")).startswith("image/") and pj.get("href"):
            return pj["href"]

    brut = entree.get("summary") or entree.get("description") or ""
    correspondance = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', brut, re.IGNORECASE)
    if correspondance:
        return correspondance.group(1)

    return None


def _extraire_date(entree):
    struct = entree.get("published_parsed") or entree.get("updated_parsed")
    if not struct:
        return None
    try:
        return datetime(*struct[:6], tzinfo=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None
