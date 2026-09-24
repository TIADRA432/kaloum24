"""Régressions ciblées du cœur éditorial et des permissions."""
import os
import re
import tempfile

os.environ.setdefault("SECRET_KEY", "cle-de-test")
os.environ["SITE_URL"] = "https://exemple.test"

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path

from app import create_app
from extensions import db
from models import User, Category, Article, ROLES, ARTICLE_STATUSES
from scheduler import publier_articles_programmes


def csrf(client, url):
    html = client.get(url).get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"Jeton CSRF introuvable sur {url}"
    return match.group(1)


def main():
    assert ROLES == ("user", "redacteur", "moderateur", "admin")
    assert ARTICLE_STATUSES == (
        "brouillon", "en_relecture", "programme", "publie", "archive"
    )

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        user = User(
            username="compte-banni",
            email="banni@example.test",
            role="redacteur",
            is_banned=True,
        )
        user.set_password("MotDePasseSolide1!")
        db.session.add(user)

        actif = User(
            username="compte-actif",
            email="actif@example.test",
            role="redacteur",
            is_banned=False,
        )
        actif.set_password("MotDePasseSolide2!")
        db.session.add(actif)

        categorie = Category(name="Tests", slug="tests")
        db.session.add(categorie)
        db.session.flush()

        publie = Article(
            title="Article déjà publié",
            slug="article-deja-publie",
            summary="Résumé suffisamment long pour le test.",
            content="<p>Contenu publié qui ne doit pas être modifiable directement.</p>",
            category_id=categorie.id,
            author_id=actif.id,
            status="publie",
        )
        db.session.add(publie)

        from datetime import datetime, timedelta
        programme = Article(
            title="Article programmé",
            slug="article-programme",
            summary="Résumé suffisamment long pour la programmation.",
            content="<p>Contenu programmé suffisamment long pour être publié.</p>",
            category_id=categorie.id,
            author_id=actif.id,
            status="programme",
            scheduled_at=datetime.utcnow() - timedelta(minutes=5),
            is_featured=True,
        )
        db.session.add(programme)
        db.session.commit()

    with app.test_client() as client:
        token = csrf(client, "/connexion")
        response = client.post(
            "/connexion",
            data={
                "csrf_token": token,
                "identifiant": "compte-banni",
                "password": "MotDePasseSolide1!",
            },
            follow_redirects=True,
        )
        body = response.get_data(as_text=True).lower()
        assert response.status_code == 200
        assert "suspendu" in body

        profile = client.get("/compte", follow_redirects=False)
        assert profile.status_code in (302, 401)

    # Une session existante doit être invalidée dès que le compte est banni.
    with app.test_client() as client:
        token = csrf(client, "/connexion")
        response = client.post(
            "/connexion",
            data={
                "csrf_token": token,
                "identifiant": "compte-actif",
                "password": "MotDePasseSolide2!",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Un rédacteur ne peut pas réécrire directement un contenu déjà publié.
        publie = client.get("/admin/articles/1/modifier", follow_redirects=False)
        assert publie.status_code == 403

        with app.app_context():
            actif = User.query.filter_by(username="compte-actif").first()
            actif.is_banned = True
            db.session.commit()

        profile = client.get("/compte", follow_redirects=False)
        assert profile.status_code in (302, 401)

    with app.app_context():
        n = publier_articles_programmes()
        assert n == 1
        programme = Article.query.filter_by(slug="article-programme").first()
        assert programme.status == "publie"
        assert programme.scheduled_at is None

    try:
        os.remove(_db_path)
    except OSError:
        pass

    print("PASS  rôles cohérents")
    print("PASS  statuts éditoriaux cohérents")
    print("PASS  compte banni bloqué à la connexion")
    print("PASS  session existante invalidée après bannissement")
    print("PASS  article publié verrouillé pour le rédacteur")
    print("PASS  programmation nettoyée après publication")


if __name__ == "__main__":
    main()
