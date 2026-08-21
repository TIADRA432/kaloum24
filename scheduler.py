"""Publication automatique des articles programmés.

Isolé dans son propre module pour que la commande CLI (`flask
publish-scheduled`, destinée à une vraie tâche planifiée) et la route admin
de déclenchement manuel (filet de sécurité si la tâche planifiée externe ne
tourne pas) partagent exactement la même logique — jamais deux implémentations
qui pourraient diverger.
"""
from datetime import datetime

from extensions import db
from models import Article


def publier_articles_programmes():
    """Fait passer en "publie" tout article "programme" dont l'heure est
    arrivée. Idempotent : un article déjà publié n'est plus concerné, le
    relancer sans article dû ne fait rien. Retourne le nombre publié."""
    maintenant = datetime.utcnow()
    articles = (
        Article.query.filter_by(status="programme")
        .filter(Article.scheduled_at <= maintenant)
        .all()
    )
    for article in articles:
        article.status = "publie"
    db.session.commit()
    return len(articles)
