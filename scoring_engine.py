"""Calcul du score de chaque article collecté (Phase 4 du plan).

Cinq composantes indépendantes, chacune 0-100, combinées selon les
pondérations de ScoringConfig (qui somment à 1.0) :

- **Fraîcheur** : décroît linéairement depuis la publication, pure fonction
  du temps, aucune configuration nécessaire.
- **Popularité** : dérivée du nombre de sources qui couvrent le même
  Topic (voir topic_matcher.py) — un article seul reste bas, un événement
  repris par plusieurs sources monte.
- **Fiabilité de la source** : directement Source.trust_level, déjà réglé
  par l'admin à la création de la source (Phase 1).
- **Pertinence thématique** : proportion des mots-clés positifs de LA
  SOURCE (Source.keywords_include) retrouvés dans le titre/extrait.
- **Importance** : présence d'un vocabulaire d'alerte GLOBAL, configurable
  (ScoringConfig.importance_keywords) — distinct de la pertinence, qui elle
  est propre à chaque source.

Volontairement simple : pas de classification par apprentissage, pas
d'analyse sémantique. Un article dont aucun signal ne se déclenche reçoit
des scores neutres (50) sur les composantes concernées plutôt que 0, pour
ne pas punir un article correct faute de configuration plutôt que faute de
qualité.
"""
from datetime import datetime, timedelta

from extensions import db
from models import CollectedArticle, ScoringConfig
from utils import liste_mots_cles, normaliser_texte

FENETRE_FRAICHEUR_HEURES = 72     # au-delà, un article tombe à 0 en fraîcheur
FENETRE_NOTATION_JOURS_DEFAUT = 7  # articles considérés pour une notation en lot


def _score_fraicheur(article):
    reference = article.published_at or article.collected_at
    if reference is None:
        return 50.0

    age_heures = (datetime.utcnow() - reference).total_seconds() / 3600
    if age_heures <= 0:
        return 100.0
    if age_heures >= FENETRE_FRAICHEUR_HEURES:
        return 0.0
    return 100.0 * (1 - age_heures / FENETRE_FRAICHEUR_HEURES)


def _score_popularite(article):
    if article.topic_id is None or article.topic is None:
        return 15.0          # source unique, événement non confirmé ailleurs

    n = article.topic.sources_count
    # 2 sources -> 50, 3 -> 85, 4+ -> 100. Le saut de 1 à 2 sources compte
    # le plus : c'est le moment où un événement passe de « annoncé par un
    # site » à « confirmé par plusieurs ».
    return min(100.0, 15.0 + (n - 1) * 35.0)


def _score_confiance(article):
    return float(article.source.trust_level)


def _score_pertinence(article):
    mots = liste_mots_cles(article.source.keywords_include)
    if not mots:
        return 50.0           # source sans préférence déclarée : neutre

    texte = normaliser_texte(f"{article.title} {article.excerpt or ''}")
    trouves = sum(1 for m in mots if m in texte)
    return min(100.0, (trouves / len(mots)) * 100.0)


def _score_importance(article, config):
    mots = liste_mots_cles(config.importance_keywords)
    if not mots:
        return 50.0

    texte = normaliser_texte(f"{article.title} {article.excerpt or ''}")
    trouves = sum(1 for m in mots if m in texte)
    return min(100.0, trouves * 25.0)   # 1 mot -> 25, 2 -> 50, 3 -> 75, 4+ -> 100


def calculer_score(article, config=None):
    """Calcule et affecte les cinq composantes + le total sur `article`.

    Ne fait PAS de commit — à charge de l'appelant, pour permettre de noter
    plusieurs articles dans une seule transaction (voir noter_articles).
    Retourne le score total pour un usage direct (aperçu admin sans écrire
    en base, par exemple).
    """
    if config is None:
        config = ScoringConfig.get_active()

    importance = _score_importance(article, config)
    fraicheur = _score_fraicheur(article)
    popularite = _score_popularite(article)
    pertinence = _score_pertinence(article)
    confiance = _score_confiance(article)

    total = (
        importance * config.weight_importance
        + fraicheur * config.weight_freshness
        + popularite * config.weight_popularity
        + pertinence * config.weight_relevance
        + confiance * config.weight_trust
    )

    article.score_importance = importance
    article.score_freshness = fraicheur
    article.score_popularity = popularite
    article.score_relevance = pertinence
    article.score_trust = confiance
    article.score_total = total

    return total


def apercu_score(article, config):
    """Comme calculer_score, mais ne modifie jamais l'objet `article` — sert
    à l'écran admin pour prévisualiser l'effet d'une pondération candidate
    sans écrire quoi que ce soit, ni en mémoire ni en base."""
    importance = _score_importance(article, config)
    fraicheur = _score_fraicheur(article)
    popularite = _score_popularite(article)
    pertinence = _score_pertinence(article)
    confiance = _score_confiance(article)

    total = (
        importance * config.weight_importance
        + fraicheur * config.weight_freshness
        + popularite * config.weight_popularity
        + pertinence * config.weight_relevance
        + confiance * config.weight_trust
    )
    return {
        "importance": importance, "fraicheur": fraicheur, "popularite": popularite,
        "pertinence": pertinence, "confiance": confiance, "total": total,
    }


def noter_articles(fenetre_jours=FENETRE_NOTATION_JOURS_DEFAUT):
    """Note (ou renote) tous les articles collectés récents.

    Renoter systématiquement plutôt que seulement les articles jamais
    encore notés : la fraîcheur décroît avec le temps et la popularité peut
    augmenter si un sujet gagne des sources après coup — un score calculé
    une seule fois à la collecte deviendrait obsolète.
    """
    config = ScoringConfig.get_active()
    limite = datetime.utcnow() - timedelta(days=fenetre_jours)

    articles = CollectedArticle.query.filter(
        CollectedArticle.collected_at >= limite
    ).all()

    for article in articles:
        calculer_score(article, config)

    db.session.commit()
    return len(articles)
