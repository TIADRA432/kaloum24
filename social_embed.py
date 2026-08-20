"""Validation des URL de publications de réseaux sociaux, avant intégration
via le widget officiel de la plateforme (jamais de récupération de contenu
côté serveur — voir README, section Réseaux sociaux).

Seul Facebook est implémenté pour l'instant, via les Embedded Posts
(https://developers.facebook.com/docs/plugins/embedded-posts/) — le seul
mécanisme que Meta fournit pour afficher un post tiers sur un site externe
sans passer par une application approuvée et un accès API. D'autres
plateformes (Instagram, X, YouTube, TikTok) pourraient s'ajouter plus tard
sur le même principe : une fonction de validation dédiée, jamais de
contournement des mécanismes officiels de la plateforme concernée.

Limite assumée, pas contournable : ce module ne vérifie que la FORME de
l'URL, jamais si le post est réellement public. Cette vérification-là
n'est possible que côté navigateur, par le widget de la plateforme
elle-même — une tentative de vérification serveur nécessiterait soit une
application Meta approuvée (processus externe, pas du code), soit un appel
qui se heurterait presque certainement à une protection anti-robot, comme
observé sur d'autres sites tout au long de ce projet. Un post privé ou
supprimé s'affichera simplement comme vide chez le lecteur — c'est le
comportement prévu par Meta lui-même (« graceful degradation »), pas une
erreur à rattraper ici.
"""
from urllib.parse import urlparse

DOMAINES_FACEBOOK = {
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "web.facebook.com", "fb.watch",
}


def valider_url_reseau_social(url):
    """Retourne (plateforme, erreur). Une seule des deux est non None.

    Un champ vide n'est pas une erreur : l'intégration d'un post est
    facultative sur un article — retourne (None, None) dans ce cas, à
    l'appelant de ne rien faire de plus.
    """
    url = (url or "").strip()
    if not url:
        return None, None

    if not url.startswith(("http://", "https://")):
        return None, "L'URL du post doit commencer par http:// ou https://."

    try:
        domaine = urlparse(url).netloc.lower()
    except ValueError:
        return None, "URL illisible."

    if domaine in DOMAINES_FACEBOOK:
        return "facebook", None

    return None, (
        "URL non reconnue comme un post Facebook. Formats acceptés : "
        "facebook.com/…/posts/…, facebook.com/watch/?v=…, fb.watch/…. "
        "Les autres plateformes ne sont pas encore prises en charge."
    )
