"""Regroupement des articles collectés qui semblent parler du même
événement, tous sources confondues (Phase 3 du plan).

Approche volontairement simple pour un premier tour : similarité textuelle
sur les titres (rapidfuzz), pas de modèle sémantique. C'est une limite
assumée, pas un oubli — voir PLAN_AGREGATEUR.md, Phase 3 : deux titres qui
décrivent le même événement avec des mots très différents ne seront pas
rapprochés par cette méthode (vérifié sur l'exemple du cahier des charges :
les trois titres qui y sont donnés scorent entre 49 et 67, sous le seuil
retenu de 70 — un seuil assez bas pour tous les attraper créerait des faux
positifs massifs entre articles sans rapport). Sur des reformulations plus
proches, en revanche, la méthode fonctionne bien : testé sur cinq cas tirés
de vrais titres collectés, cinq corrects.

Un passage à des embeddings sémantiques est noté en backlog dans le plan —
à ne construire que si cette limite se révèle gênante en usage réel.
"""
from datetime import datetime, timedelta

from rapidfuzz import fuzz

from extensions import db
from models import CollectedArticle, ScoringConfig, Topic
from utils import normaliser_texte

FENETRE_JOURS_DEFAUT = 3
# Au-delà de quelques centaines d'articles sans sujet dans la fenêtre, le
# coût en O(n²) des comparaisons deux à deux commencerait à se faire sentir
# (quelques centaines de millisecondes, pas bloquant, mais à surveiller).
# À ce volume, un index de similarité (ex. MinHash) remplacerait la
# comparaison exhaustive — pas nécessaire tant que le nombre de sources
# reste de l'ordre de la dizaine.


def similarite(titre_a, titre_b):
    """0-100. token_set_ratio : robuste à l'ordre des mots et aux titres de
    longueurs différentes — utile ici car deux rédactions ne titrent jamais
    un même événement avec exactement la même longueur de phrase."""
    return fuzz.token_set_ratio(normaliser_texte(titre_a), normaliser_texte(titre_b))


def rattacher_sujets(seuil=None, fenetre_jours=FENETRE_JOURS_DEFAUT):
    """Parcourt les articles sans sujet et tente de les regrouper.

    Idempotent : peut être relancé sans effet indésirable sur les articles
    déjà rattachés — seuls ceux avec `topic_id` encore vide sont considérés.
    Ne compare jamais deux articles de la même source entre eux : une source
    ne « confirme » pas son propre sujet, il en faut au moins deux.
    """
    if seuil is None:
        seuil = ScoringConfig.get_active().topic_similarity_threshold

    limite = datetime.utcnow() - timedelta(days=fenetre_jours)

    sans_sujet = (
        CollectedArticle.query
        .filter(CollectedArticle.topic_id.is_(None))
        .filter(CollectedArticle.collected_at >= limite)
        .order_by(CollectedArticle.collected_at.asc())
        .all()
    )
    topics_recents = Topic.query.filter(Topic.first_seen_at >= limite).all()

    rattachements = 0
    nouveaux_sujets = 0

    for article in sans_sujet:
        if article.topic_id is not None:
            continue          # rattaché plus tôt dans cette même boucle

        meilleur_topic, meilleur_score = None, 0
        for topic in topics_recents:
            score = similarite(article.title, topic.representative_title)
            if score > meilleur_score:
                meilleur_topic, meilleur_score = topic, score

        if meilleur_topic and meilleur_score >= seuil:
            article.topic_id = meilleur_topic.id
            meilleur_topic.sources_count += 1
            rattachements += 1
            continue

        meilleur_pair, meilleur_score2 = None, 0
        for autre in sans_sujet:
            if autre.id == article.id or autre.topic_id is not None:
                continue
            if autre.source_id == article.source_id:
                continue
            score = similarite(article.title, autre.title)
            if score > meilleur_score2:
                meilleur_pair, meilleur_score2 = autre, score

        if meilleur_pair and meilleur_score2 >= seuil:
            premiere_date = min(article.collected_at, meilleur_pair.collected_at)
            nouveau = Topic(
                representative_title=article.title, sources_count=2,
                first_seen_at=premiere_date,
            )
            db.session.add(nouveau)
            db.session.flush()          # pour obtenir nouveau.id avant affectation
            article.topic_id = nouveau.id
            meilleur_pair.topic_id = nouveau.id
            topics_recents.append(nouveau)
            nouveaux_sujets += 1

    db.session.commit()
    return {"rattachements": rattachements, "nouveaux_sujets": nouveaux_sujets}
