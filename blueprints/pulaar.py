"""Module Pulaar — routes publiques. Voir PLAN_PULAAR.md.

Volontairement séparé de blueprints/main.py : ce module a sa propre
identité visuelle (Tiadra Consortium, voir static/css/pulaar.css) et sa
propre logique, pas une extension du site éditorial existant.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required

from extensions import db
from models import PulaarTerm, PulaarDefinition, PulaarDomain, PulaarProposal
from pulaar_i18n import t as traduire, couverture_pulaar

pulaar_bp = Blueprint("pulaar", __name__, url_prefix="/pulaar")


@pulaar_bp.context_processor
def _injecter_traductions():
    """Rend `t()` et la langue courante disponibles dans les gabarits DE CE
    BLUEPRINT uniquement (context_processor, pas app_context_processor :
    sinon ces variables fuiteraient dans tous les gabarits du site).
    La langue vit dans l'URL (?lang=ff) plutôt qu'en session : un lien
    partagé garde la langue choisie, et rien à stocker côté serveur."""
    langue = request.args.get("lang", "fr")
    if langue not in ("fr", "ff"):
        langue = "fr"
    traduites, total = couverture_pulaar()
    return {
        "t": lambda cle: traduire(cle, langue),
        "langue_ui": langue,
        "couverture_pulaar": (traduites, total),
    }


@pulaar_bp.route("/", strict_slashes=False)
def accueil():
    q = request.args.get("q", "").strip()
    resultats = []
    if q:
        motif = f"%{q}%"
        resultats = (
            PulaarTerm.query.join(PulaarDefinition)
            .filter(db.or_(PulaarTerm.lemma.ilike(motif), PulaarDefinition.text.ilike(motif)))
            .distinct()
            .limit(30)
            .all()
        )
    domaines = PulaarDomain.query.order_by(PulaarDomain.name).all()
    total_termes = PulaarTerm.query.count()
    # Sans recherche, on liste quand même les termes : autrement un visiteur
    # arrive sur une page vide et doit deviner quoi chercher pour voir
    # quoi que ce soit (constaté sur la vraie page en production).
    tous_termes = [] if q else PulaarTerm.query.order_by(PulaarTerm.lemma).limit(100).all()
    return render_template(
        "pulaar/accueil.html", q=q, resultats=resultats, domaines=domaines,
        total_termes=total_termes, tous_termes=tous_termes,
    )


@pulaar_bp.route("/terme/<slug>")
def terme(slug):
    t = PulaarTerm.query.filter_by(slug=slug).first_or_404()
    return render_template("pulaar/terme.html", terme=t)


@pulaar_bp.route("/domaine/<slug>")
def domaine(slug):
    d = PulaarDomain.query.filter_by(slug=slug).first_or_404()
    termes = PulaarTerm.query.filter_by(domain_id=d.id).order_by(PulaarTerm.lemma).all()
    return render_template("pulaar/domaine.html", domaine=d, termes=termes)


@pulaar_bp.route("/proposer", methods=["GET", "POST"])
@login_required
def proposer():
    domaines = PulaarDomain.query.order_by(PulaarDomain.name).all()
    if request.method == "POST":
        lemme = request.form.get("term_lemma", "").strip()
        definition = request.form.get("definition_fr", "").strip()
        if len(lemme) < 1 or len(definition) < 5:
            flash("Indique au moins le mot pulaar et une définition en français "
                 "(5 caractères minimum).", "error")
            return render_template("pulaar/proposer.html", domaines=domaines)

        domain_id = request.form.get("domain_id", type=int)
        db.session.add(PulaarProposal(
            term_lemma=lemme,
            definition_fr=definition,
            domain_id=domain_id if domain_id else None,
            justification=request.form.get("justification", "").strip() or None,
            proposed_by_id=current_user.id,
        ))
        db.session.commit()
        flash("Merci — ta proposition part en relecture avant toute publication.", "success")
        return redirect(url_for("pulaar.accueil"))

    return render_template("pulaar/proposer.html", domaines=domaines)
