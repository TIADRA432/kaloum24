"""Comptage des lectures d'articles, tamponné en mémoire.

Pourquoi ce module existe : incrémenter le compteur directement à chaque
consultation produit une écriture en base par visiteur. SQLite verrouille
toute la base pendant une écriture — un article partagé sur WhatsApp et ouvert
par quelques centaines de personnes en même temps mettrait ces écritures en
file d'attente et ralentirait tout le site, à cause d'un simple compteur.

Ici, les vues s'accumulent en mémoire et sont écrites par lots (toutes les
FLUSH_INTERVAL secondes au plus). Le nombre d'écritures devient constant quel
que soit le trafic.

Compromis assumés :
- Les vues accumulées depuis la dernière écriture sont perdues si le processus
  s'arrête brutalement. Pour un compteur de lectures, c'est sans conséquence.
- Avec plusieurs workers gunicorn, chacun a son propre tampon ; les totaux
  restent corrects puisque chaque lot est ajouté (UPDATE ... + n) et non écrasé.
"""
import threading
import time

from sqlalchemy import text as sql_text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db

FLUSH_INTERVAL = 30          # secondes entre deux écritures au plus
FLUSH_THRESHOLD = 50         # ou dès que ce nombre de vues est en attente

_tampon = {}                 # {article_id: nombre de vues en attente}
_dernier_vidage = time.time()
_verrou = threading.Lock()


def enregistrer_vue(app, article_id):
    """Comptabilise une lecture. Écrit en base seulement de temps en temps."""
    global _dernier_vidage

    with _verrou:
        _tampon[article_id] = _tampon.get(article_id, 0) + 1
        total_en_attente = sum(_tampon.values())
        assez_ancien = (time.time() - _dernier_vidage) >= FLUSH_INTERVAL

        if not (assez_ancien or total_en_attente >= FLUSH_THRESHOLD):
            return

        a_ecrire = dict(_tampon)
        _tampon.clear()
        _dernier_vidage = time.time()

    _ecrire(app, a_ecrire)


def _ecrire(app, compteurs):
    """Applique les vues accumulées, en une seule transaction."""
    if not compteurs:
        return
    try:
        for article_id, n in compteurs.items():
            # SQL direct plutôt qu'un update ORM : l'ORM déclencherait le
            # `onupdate` de la colonne updated_at, si bien que chaque lecture
            # ferait passer l'article pour modifié — ce que le sitemap
            # signalerait aux moteurs de recherche à tort.
            # L'incrément relatif évite aussi que deux workers s'écrasent.
            db.session.execute(
                sql_text("UPDATE articles SET views = views + :n WHERE id = :id"),
                {"n": n, "id": article_id},
            )
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        app.logger.warning("Échec d'écriture des compteurs de vues : %s", exc)


def vider_maintenant(app):
    """Force l'écriture immédiate du tampon (arrêt du serveur, tests)."""
    global _dernier_vidage
    with _verrou:
        a_ecrire = dict(_tampon)
        _tampon.clear()
        _dernier_vidage = time.time()
    _ecrire(app, a_ecrire)


def vues_en_attente(article_id=None):
    """Vues pas encore écrites — sert à afficher un total juste à l'écran."""
    with _verrou:
        if article_id is None:
            return dict(_tampon)
        return _tampon.get(article_id, 0)
