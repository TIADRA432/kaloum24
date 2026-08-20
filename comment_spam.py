"""Détection heuristique de spam sur les commentaires.

Volontairement simple : pas de modèle de classification, des règles
lisibles et réglables depuis la configuration. Un commentaire jugé suspect
n'est jamais rejeté silencieusement — il part en file de modération, comme
n'importe quel commentaire quand la pré-modération est active. Le rôle de
ce module est seulement de décider, quand COMMENT_AUTO_APPROVE est activé,
ce qui peut s'afficher tout de suite et ce qui doit attendre un humain.
"""
import re
from datetime import datetime, timedelta

from utils import liste_mots_cles, normaliser_texte

URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
REPETITION_RE = re.compile(r"(.)\1{7,}")           # ex. "!!!!!!!!" ou "aaaaaaaa"
FENETRE_FLOOD_MINUTES = 10


def evaluer(contenu, config, user_id=None, model_comment=None):
    """Retourne (suspect: bool, raisons: list[str]).

    `model_comment` est passé en paramètre plutôt qu'importé directement,
    pour que ce module reste testable sans dépendre de l'ordre d'import de
    models.py (qui importe déjà pas mal de choses).
    """
    raisons = []
    texte_normalise = normaliser_texte(contenu)

    max_liens = config["COMMENT_MAX_LIENS"]
    nb_liens = len(URL_RE.findall(contenu))
    if nb_liens > max_liens:
        raisons.append(f"{nb_liens} lien(s) — au-delà de la limite ({max_liens})")

    mots_interdits = liste_mots_cles(config["COMMENT_SPAM_KEYWORDS"])
    trouves = [m for m in mots_interdits if m in texte_normalise]
    if trouves:
        raisons.append("vocabulaire suspect (" + ", ".join(trouves[:3]) + ")")

    if REPETITION_RE.search(contenu):
        raisons.append("caractères répétés de façon excessive")

    majuscules = sum(1 for c in contenu if c.isupper())
    lettres = sum(1 for c in contenu if c.isalpha())
    if lettres >= 20 and majuscules / lettres > 0.7:
        raisons.append("tout en majuscules")

    if model_comment is not None and user_id is not None:
        limite = datetime.utcnow() - timedelta(minutes=FENETRE_FLOOD_MINUTES)
        recent_identique = (
            model_comment.query.filter_by(user_id=user_id, content=contenu)
            .filter(model_comment.created_at >= limite)
            .first()
        )
        if recent_identique:
            raisons.append("contenu identique à un commentaire récent du même compte (flood)")

    return (len(raisons) > 0, raisons)
