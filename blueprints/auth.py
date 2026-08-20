import re

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, limiter
from mailer import send_email
from models import User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/inscription", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_REGISTER"], methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        errors = []
        if len(username) < 3:
            errors.append("Le pseudo doit faire au moins 3 caractères.")
        elif not re.match(r"^[\w .\-]+$", username):
            errors.append("Le pseudo contient des caractères non autorisés.")
        if not EMAIL_RE.match(email):
            errors.append("Adresse e-mail invalide.")
        if len(password) < 8:
            errors.append("Le mot de passe doit faire au moins 8 caractères.")
        if password != password_confirm:
            errors.append("Les mots de passe ne correspondent pas.")
        if User.query.filter_by(username=username).first():
            errors.append("Ce pseudo est déjà pris.")
        if User.query.filter_by(email=email).first():
            errors.append("Cette adresse e-mail est déjà utilisée.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", username=username, email=email)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Bienvenue, {user.username} !", "success")
        return redirect(url_for("main.home"))

    return render_template("register.html")


@auth_bp.route("/connexion", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_LOGIN"], methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter(
            db.or_(User.username == identifiant, User.email == identifiant.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Content de te revoir, {user.username}.", "success")
            next_url = request.args.get("next")
            # On n'accepte qu'une redirection interne, pour éviter qu'un lien
            # piégé renvoie l'utilisateur vers un site tiers après connexion.
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("main.home"))

        flash("Identifiant ou mot de passe incorrect.", "error")

    return render_template("login.html")


@auth_bp.route("/deconnexion")
@login_required
def logout():
    logout_user()
    flash("Tu es déconnecté.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/compte")
@login_required
def profile():
    return render_template("profile.html")


@auth_bp.route("/compte/mot-de-passe", methods=["POST"])
@login_required
def change_password():
    actuel = request.form.get("actuel", "")
    nouveau = request.form.get("nouveau", "")
    confirmation = request.form.get("confirmation", "")

    if not current_user.check_password(actuel):
        flash("Mot de passe actuel incorrect.", "error")
    elif len(nouveau) < 8:
        flash("Le nouveau mot de passe doit faire au moins 8 caractères.", "error")
    elif nouveau != confirmation:
        flash("Les deux nouveaux mots de passe ne correspondent pas.", "error")
    else:
        current_user.set_password(nouveau)
        db.session.commit()
        flash("Mot de passe modifié.", "success")

    return redirect(url_for("auth.profile"))


# ------------------------------------------------- mot de passe oublié

@auth_bp.route("/mot-de-passe-oublie", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_PASSWORD_RESET"], methods=["POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            token = user.reset_token()
            lien = url_for("auth.reset_password", token=token, _external=True)
            send_email(
                user.email,
                f"Réinitialisation de ton mot de passe — {current_app.config['SITE_NAME']}",
                "Bonjour,\n\n"
                "Tu as demandé à réinitialiser ton mot de passe. Ouvre ce lien "
                "dans l'heure qui vient :\n\n"
                f"{lien}\n\n"
                "Si tu n'es pas à l'origine de cette demande, ignore ce message : "
                "ton mot de passe reste inchangé.\n",
            )

        # Même message dans tous les cas : révéler qu'une adresse existe ou non
        # permettrait d'énumérer les comptes du site.
        flash(
            "Si un compte est associé à cette adresse, un lien de réinitialisation "
            "vient d'être envoyé.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/reinitialiser/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    user = User.verify_reset_token(token)
    if not user:
        flash("Ce lien est invalide ou a expiré. Refais une demande.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirmation = request.form.get("password_confirm", "")

        if len(password) < 8:
            flash("Le mot de passe doit faire au moins 8 caractères.", "error")
        elif password != confirmation:
            flash("Les mots de passe ne correspondent pas.", "error")
        else:
            user.set_password(password)
            db.session.commit()
            flash("Mot de passe réinitialisé. Tu peux te connecter.", "success")
            return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
