import os
import click
from datetime import datetime

from flask import Flask, render_template
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import db, login_manager, csrf, migrate, limiter
from security import (
    enregistrer_entetes_securite, appliquer_verification_demarrage,
    configurer_journalisation, verifier_configuration,
)
from models import User, Category, Article, Comment, CollectedArticle
from utils import (
    fr_date, fr_datetime, time_ago, rfc822,
    strip_html, excerpt, reading_time,
)

load_dotenv()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    configurer_journalisation(app)

    # Derrière Nginx, les en-têtes X-Forwarded-* portent la vraie IP et le
    # vrai schéma. Sans ProxyFix, Flask croit que toutes les requêtes viennent
    # du proxy en HTTP : la limitation de débit deviendrait globale au lieu
    # d'être par visiteur, et les URL générées seraient en http://.
    if app.config["PROXY_COUNT"] > 0:
        n = app.config["PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=n, x_prefix=n)

    if app.config["WHATSAPP_ACCESS_TOKEN"] and not app.config["WHATSAPP_APP_SECRET"]:
        app.logger.warning(
            "WHATSAPP_ACCESS_TOKEN est configuré mais WHATSAPP_APP_SECRET est vide : "
            "le webhook WhatsApp accepte des requêtes sans vérifier leur origine. "
            "À corriger avant la mise en production."
        )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    # Flask-Limiter lit RATELIMIT_STORAGE_URI et RATELIMIT_ENABLED depuis
    # app.config au moment de l'initialisation.
    limiter.init_app(app)

    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.admin import admin_bp
    from blueprints.payments import payments_bp
    from blueprints.whatsapp import whatsapp_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(whatsapp_bp)

    # Le webhook Stripe et le webhook WhatsApp sont tous deux signés par leur
    # fournisseur respectif, sans session : pas de jeton CSRF possible.
    csrf.exempt(payments_bp)
    csrf.exempt(whatsapp_bp)

    for name, func in (
        ("fr_date", fr_date), ("fr_datetime", fr_datetime), ("time_ago", time_ago),
        ("rfc822", rfc822), ("strip_html", strip_html), ("excerpt", excerpt),
        ("reading_time", reading_time),
    ):
        app.jinja_env.filters[name] = func

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        socials = [
            ("X", app.config["SOCIAL_X"], "x"),
            ("WhatsApp", app.config["SOCIAL_WHATSAPP_CHANNEL"], "whatsapp"),
            ("Facebook", app.config["SOCIAL_FACEBOOK"], "facebook"),
            ("YouTube", app.config["SOCIAL_YOUTUBE"], "youtube"),
            ("Instagram", app.config["SOCIAL_INSTAGRAM"], "instagram"),
            ("TikTok", app.config["SOCIAL_TIKTOK"], "tiktok"),
        ]
        contexte = {
            "site_name": app.config["SITE_NAME"],
            "site_tagline": app.config["SITE_TAGLINE"],
            "site_url": app.config["SITE_URL"],
            "today_label": fr_date(datetime.utcnow(), with_weekday=True),
            "current_year": datetime.utcnow().year,
            "social_links": [s for s in socials if s[1]],
            "nav_categories": [],
            "ticker_articles": [],
            "pending_comments_count": 0,
            "pending_collected_count": 0,
        }

        # Ce processeur s'exécute pour TOUT rendu de gabarit, y compris les
        # pages d'erreur. Si la base est absente ou indisponible, les valeurs
        # de repli ci-dessus permettent d'afficher quand même la page
        # d'erreur — sans quoi l'échec se reproduirait pendant le rendu et
        # masquerait le message utile.
        try:
            contexte["nav_categories"] = Category.query.order_by(Category.name).all()
            contexte["ticker_articles"] = (
                Article.query.filter_by(status="publie")
                .order_by(Article.created_at.desc())
                .limit(8)
                .all()
            )
            contexte["pending_comments_count"] = (
                Comment.query.filter_by(status="en_attente").count()
            )
            contexte["pending_collected_count"] = (
                CollectedArticle.query.filter_by(status="nouveau").count()
            )
        except OperationalError:
            db.session.rollback()

        return contexte

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(413)
    def too_large(e):
        return render_template("413.html"), 413

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("429.html", description=getattr(e, "description", "")), 429

    @app.errorhandler(OperationalError)
    def base_non_initialisee(error):
        """Rattrape le cas « no such table » et explique quoi faire.

        SQLite crée un fichier vide à la première connexion : sans cette
        vérification, oublier `flask db upgrade` produit une trace SQLAlchemy
        de 80 lignes qui n'indique nulle part la commande manquante. C'est
        l'erreur la plus fréquente à la première installation.
        """
        if "no such table" in str(error.orig).lower():
            app.logger.error(
                "Base de données non initialisée. Lance : flask db upgrade"
            )
            return render_template("erreur_base.html"), 500
        raise error

    @app.errorhandler(500)
    def erreur_interne(e):
        return render_template("500.html"), 500

    # Les vues accumulées en mémoire sont écrites avant l'arrêt du processus,
    # pour ne pas perdre le comptage du dernier intervalle.
    import atexit
    import view_counter

    @atexit.register
    def _vider_compteurs():
        try:
            with app.app_context():
                view_counter.vider_maintenant(app)
        except Exception:
            pass          # arrêt en cours : on ne bloque jamais là-dessus

    enregistrer_entetes_securite(app)
    appliquer_verification_demarrage(app)

    # ------------------------------------------------------ commandes CLI
    @app.cli.command("init-db")
    def init_db():
        """Crée les tables de la base de données."""
        db.create_all()
        print("Base de données initialisée.")

    @app.cli.command("seed-db")
    def seed_db():
        """Remplit la base avec des données de démonstration."""
        from seed import run_seed
        run_seed()

    @app.cli.command("seed-sources")
    def seed_sources():
        """Enregistre les sources d'agrégation vérifiées (voir PLAN_AGREGATEUR.md).

        Toutes créées inactives : à activer une par une depuis l'admin, en
        connaissance de cause.
        """
        from seed_sources import run_seed_sources
        run_seed_sources()

    @app.cli.command("collect-sources")
    @click.option("--force", is_flag=True,
                 help="Ignore la fréquence configurée : collecte toutes les sources actives.")
    def collect_sources_cmd(force):
        """Collecte les nouveaux articles des sources actives et conformes.

        À lancer périodiquement via cron (voir deploiement/). Une source
        inactive ou dont la conformité n'a pas été cochée n'est jamais
        interrogée.
        """
        from collector import run_collection
        resultats = run_collection(forcer=force)

        if not resultats:
            print("Aucune source active et conforme à collecter.")
            return

        for r in resultats:
            if r["statut"] == "ignore":
                print(f"  {r['source']:<25} ignorée (fréquence non échue)")
            elif r["statut"] == "bloque":
                print(f"  {r['source']:<25} BLOQUÉE : {r['erreur']}")
            elif r["statut"] == "erreur":
                print(f"  {r['source']:<25} ERREUR : {r['erreur']}")
            elif r["statut"] == "sujets":
                print(f"  {r['source']:<25} {r['nouveaux_sujets']} nouveau(x) sujet(s), "
                     f"{r['rattachements']} article(s) rattaché(s) à un sujet existant")
            elif r["statut"] == "score":
                print(f"  {r['source']:<25} {r['notes']} article(s) noté(s)")
            else:
                print(f"  {r['source']:<25} {r['nouveaux']} nouvel(aux) article(s)")

        total = sum(r["nouveaux"] for r in resultats)
        print(f"\n{total} nouvel(aux) article(s) collecté(s) au total.")

    @app.cli.command("create-admin")
    def create_admin():
        """Crée un compte administrateur de façon interactive."""
        import getpass
        username = input("Pseudo : ").strip()
        email = input("E-mail : ").strip().lower()
        password = getpass.getpass("Mot de passe : ")
        if len(password) < 8:
            print("Mot de passe trop court (8 caractères minimum).")
            return
        if User.query.filter((User.username == username) | (User.email == email)).first():
            print("Ce pseudo ou cet e-mail est déjà utilisé.")
            return
        user = User(username=username, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Administrateur « {username} » créé.")

    @app.cli.command("check-prod")
    def check_prod():
        """Audite la configuration avant une mise en production."""
        erreurs, avertissements = verifier_configuration(app, strict=True)

        print("\n=== Audit de configuration ===\n")
        if not erreurs and not avertissements:
            print("  Aucun problème détecté.\n")
        for e in erreurs:
            print("  [BLOQUANT]     " + e)
        for a in avertissements:
            print("  [AVERTISSEMENT] " + a)

        # Points qui ne se vérifient pas depuis la configuration seule.
        print("\n=== À vérifier à la main ===\n")
        rappels = [
            "Les comptes de démonstration (admin / lecteur) sont supprimés ou leurs mots de passe changés.",
            "Une sauvegarde a été restaurée avec succès au moins une fois.",
            "Le site tourne derrière gunicorn + Nginx en HTTPS, pas avec « flask run ».",
            "Les images envoyées survivent à un redéploiement (volume persistant ou stockage objet).",
            "Une surveillance est en place (au minimum un ping externe qui alerte si le site tombe).",
        ]
        for r in rappels:
            print("  [ ] " + r)
        print()

        if erreurs:
            raise SystemExit(1)

    @app.shell_context_processor
    def make_shell_context():
        return {"db": db, "User": User, "Category": Category,
                "Article": Article, "Comment": Comment}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
