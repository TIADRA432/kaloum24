"""Moteur de collecte périodique des sources d'agrégation (Phase 2 du plan).

Isolé de la commande CLI et des routes pour que les tests puissent simuler
feed_client.fetch_feed et feed_client.robots_autorise sans appel réseau réel
— même principe que les autres modules externes du projet (whatsapp_client,
feed_client).

Ce module ne fait QUE collecter (Mode 1 : titre, extrait, lien). Il ne
score pas les articles (Phase 4) et ne les regroupe pas par sujet (Phase 3)
— ils arrivent tous en statut "nouveau", prêts pour les phases suivantes.
"""
import time
from datetime import datetime, timedelta

import feed_client
import scoring_engine
import topic_matcher
from extensions import db
from models import CollectedArticle, Source
from utils import liste_mots_cles, normaliser_texte

# Pause entre deux sources, même de domaines différents : une politesse de
# base qui évite de créer un pic de requêtes sortantes d'un coup depuis le
# même serveur. S'ajoute au crawl-delay spécifique d'une source si robots.txt
# en réclame un plus long.
DELAI_ENTRE_SOURCES_SECONDES = 2


def _frequence_echue(source):
    if source.last_fetched_at is None:
        return True
    limite = timedelta(minutes=source.fetch_frequency_minutes)
    return datetime.utcnow() - source.last_fetched_at >= limite


def _passe_filtre_mots_cles(item, source):
    """Premier tri grossier, avant même l'enregistrement en base.

    Le scoring fin (Phase 4) affinera ensuite le classement de ce qui passe
    ce filtre — ceci n'élimine que ce que l'admin a explicitement exclu, ou
    ce qui ne correspond à aucun mot-clé positif quand la source en définit.
    """
    texte = normaliser_texte(f"{item['title']} {item.get('excerpt') or ''}")

    exclus = liste_mots_cles(source.keywords_exclude)
    if exclus and any(mot in texte for mot in exclus):
        return False

    inclus = liste_mots_cles(source.keywords_include)
    if inclus:
        return any(mot in texte for mot in inclus)

    return True


def collecter_source(source):
    """Collecte une seule source. Retourne un dict de résultat.

    Ne lève jamais d'exception vers l'appelant : une source en échec ne doit
    jamais interrompre la collecte des autres. Toute erreur est capturée,
    consignée sur la source elle-même (`last_error`), et retournée.
    """
    autorise, crawl_delay = feed_client.robots_autorise(source.feed_url)
    if not autorise:
        message = "robots.txt interdit désormais l'accès à ce flux — collecte suspendue."
        source.last_error = message
        source.last_fetched_at = datetime.utcnow()
        db.session.commit()
        return {"source": source.name, "statut": "bloque", "nouveaux": 0, "erreur": message}

    try:
        items = feed_client.fetch_feed(source.feed_url)
    except Exception as exc:
        message = str(exc)[:300]
        source.last_error = message
        source.last_fetched_at = datetime.utcnow()
        db.session.commit()
        return {"source": source.name, "statut": "erreur", "nouveaux": 0, "erreur": message}

    nouveaux = 0
    for item in items:
        if not _passe_filtre_mots_cles(item, source):
            continue

        deja_connu = CollectedArticle.query.filter_by(
            source_id=source.id, external_url=item["url"]
        ).first()
        if deja_connu:
            continue

        db.session.add(CollectedArticle(
            source_id=source.id,
            external_url=item["url"],
            title=item["title"],
            excerpt=item.get("excerpt"),
            # Le contenu intégral n'est conservé que si CETTE source est
            # explicitement en mode "integral" — feed_client.py peut avoir
            # extrait du contenu intégral de n'importe quel flux qui le
            # propose techniquement, mais le décider n'est pas de son
            # ressort. Une source "extrait" ne stocke jamais content_full,
            # même si le flux en fournissait un.
            content_full=(item.get("content_full") if source.content_mode == "integral" else None),
            image_url=item.get("image_url"),
            author=item.get("author"),
            published_at=item.get("published_at"),
            language="fr",
            status="nouveau",
        ))
        nouveaux += 1

    source.last_error = None
    source.last_fetched_at = datetime.utcnow()
    db.session.commit()

    return {
        "source": source.name, "statut": "ok", "nouveaux": nouveaux,
        "erreur": None, "delai_supplementaire": crawl_delay,
    }


def run_collection(forcer=False, pause=True):
    """Parcourt les sources actives et conformes dont la fréquence est échue.

    `forcer=True` : ignore la fréquence configurée (utile pour un test manuel
    ou un rattrapage après une longue panne). `pause=False` : désactive les
    délais de politesse entre sources — réservé aux tests automatisés.
    """
    resultats = []
    sources = Source.query.filter_by(is_active=True, compliance_checked=True).all()

    for i, source in enumerate(sources):
        if not forcer and not _frequence_echue(source):
            resultats.append({
                "source": source.name, "statut": "ignore",
                "nouveaux": 0, "erreur": None,
            })
            continue

        resultat = collecter_source(source)
        resultats.append(resultat)

        if pause and i < len(sources) - 1:
            attente = DELAI_ENTRE_SOURCES_SECONDES
            if resultat.get("delai_supplementaire"):
                attente = max(attente, resultat["delai_supplementaire"])
            time.sleep(attente)

    # Le regroupement par sujet a besoin de voir les nouveaux articles de
    # TOUTES les sources ensemble — deux articles proches mais collectés
    # depuis des sources différentes ne peuvent se rencontrer qu'ici, pas
    # source par source pendant la boucle ci-dessus.
    if any(r["statut"] == "ok" and r["nouveaux"] > 0 for r in resultats):
        stats_sujets = topic_matcher.rattacher_sujets()
        resultats.append({
            "source": "(regroupement par sujet)", "statut": "sujets",
            "nouveaux": 0, "erreur": None, **stats_sujets,
        })

        # Le scoring vient après le regroupement, jamais avant : la
        # composante « popularité » dépend du nombre de sources par sujet,
        # qui vient tout juste d'être mis à jour ci-dessus.
        nb_notes = scoring_engine.noter_articles()
        resultats.append({
            "source": "(scoring)", "statut": "score",
            "nouveaux": 0, "erreur": None, "notes": nb_notes,
        })

    return resultats
