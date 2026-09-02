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
from utils import slugify

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
        # Beaucoup de claviers ne permettent pas de taper ɗ, ɓ, ŋ, ƴ. Une
        # recherche qui les exigerait rendrait le dictionnaire inutilisable
        # pour une bonne partie des gens (vérifié : « taskotoodo » ne
        # trouvait pas « Taskotooɗo »). On cherche donc TOUJOURS aussi dans
        # le slug, qui est la forme translittérée du lemme.
        motif_simplifie = f"%{slugify(q).replace('-', '%')}%"
        resultats = (
            PulaarTerm.query.join(PulaarDefinition)
            .filter(db.or_(
                PulaarTerm.lemma.ilike(motif),
                PulaarDefinition.text.ilike(motif),
                PulaarTerm.slug.ilike(motif_simplifie),
            ))
            .distinct()
            .limit(30)
            .all()
        )
    domaines = PulaarDomain.query.order_by(PulaarDomain.name).all()
    total_termes = PulaarTerm.query.count()
    # Couverture monolingue : combien de termes ont réellement une
    # définition EN pulaar. Affiché tel quel, même à 0 — l'objectif est un
    # dictionnaire monolingue, autant montrer honnêtement la distance
    # restante plutôt que de la masquer.
    termes_monolingues = (
        PulaarTerm.query.join(PulaarDefinition)
        .filter(PulaarDefinition.lang == "ff").distinct().count()
    )
    # Sans recherche, on liste quand même les termes : autrement un visiteur
    # arrive sur une page vide et doit deviner quoi chercher pour voir
    # quoi que ce soit (constaté sur la vraie page en production).
    tous_termes = [] if q else PulaarTerm.query.order_by(PulaarTerm.lemma).limit(100).all()
    return render_template(
        "pulaar/accueil.html", q=q, resultats=resultats, domaines=domaines,
        total_termes=total_termes, tous_termes=tous_termes,
        termes_monolingues=termes_monolingues,
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
        definition_ff = request.form.get("definition_ff", "").strip()
        # Au moins UNE des deux définitions suffit : exiger le français
        # empêcherait un locuteur pulaar de contribuer en pulaar seul, ce
        # qui est précisément l'objectif du dictionnaire monolingue.
        if len(lemme) < 1 or (len(definition) < 5 and len(definition_ff) < 5):
            flash("Indique le mot pulaar et au moins une définition — en pulaar ou en "
                 "français (5 caractères minimum).", "error")
            return render_template("pulaar/proposer.html", domaines=domaines)

        domain_id = request.form.get("domain_id", type=int)
        db.session.add(PulaarProposal(
            term_lemma=lemme,
            definition_fr=definition,
            definition_ff=definition_ff or None,
            domain_id=domain_id if domain_id else None,
            justification=request.form.get("justification", "").strip() or None,
            proposed_by_id=current_user.id,
        ))
        db.session.commit()
        flash("Merci — ta proposition part en relecture avant toute publication.", "success")
        return redirect(url_for("pulaar.accueil"))

    return render_template("pulaar/proposer.html", domaines=domaines)
