import html as html_module
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort,
)
from flask_login import login_required, current_user

from extensions import db
from models import (
    Article, Category, Comment, User, Correspondent, Source,
    CollectedArticle, ScoringConfig, Topic, COLLECTED_STATUSES, ModerationLog,
    ArticleSource, EditorialComment, ArticleRevision, ARTICLE_TYPES, TYPES_SOURCE_ARTICLE,
    PulaarTerm, PulaarDefinition, PulaarDomain, PulaarSource, PulaarProposal,
    PULAAR_TERM_STATUTS, PULAAR_PROPOSAL_STATUTS,
)
from utils import (
    moderator_required, admin_required, redacteur_required, unique_slug,
    sanitize_html, strip_html, save_uploaded_image, normalize_phone,
)
import collector
import feed_client
import scoring_engine
import topic_matcher
from social_embed import valider_url_reseau_social

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@moderator_required
def dashboard():
    limite_24h = datetime.utcnow() - timedelta(hours=24)
    limite_7j = datetime.utcnow() - timedelta(days=7)

    stats = {
        "articles": Article.query.count(),
        "articles_publies": Article.query.filter_by(status="publie").count(),
        "brouillons": Article.query.filter_by(status="brouillon").count(),
        "en_relecture": Article.query.filter_by(status="en_relecture").count(),
        "programmes": Article.query.filter_by(status="programme").count(),
        "commentaires_en_attente": Comment.query.filter_by(status="en_attente").count(),
        "commentaires_signales": Comment.query.filter_by(reported=True).count(),
        "utilisateurs": User.query.count(),
        "abonnes": User.query.filter_by(is_subscriber=True).count(),
        "lectures": db.session.query(db.func.sum(Article.views)).scalar() or 0,
        "whatsapp_en_attente": Article.query.filter_by(
            source="whatsapp", status="brouillon"
        ).count(),
        "correspondants_actifs": Correspondent.query.filter_by(is_active=True).count(),
        # Supervision de l'agrégation (Phase 6 du plan)
        "sources_actives": Source.query.filter_by(is_active=True).count(),
        "sources_en_erreur": Source.query.filter(Source.last_error.isnot(None)).count(),
        "collectes_24h": CollectedArticle.query.filter(
            CollectedArticle.collected_at >= limite_24h
        ).count(),
        "collectes_7j": CollectedArticle.query.filter(
            CollectedArticle.collected_at >= limite_7j
        ).count(),
        "a_traiter": CollectedArticle.query.filter_by(status="nouveau").count(),
        "acceptes": CollectedArticle.query.filter_by(status="accepte").count(),
        "doublons_detectes": Topic.query.filter(Topic.sources_count >= 2).count(),
        "articles_ignores": CollectedArticle.query.filter(
            CollectedArticle.status.in_(["rejete", "archive"])
        ).count(),
    }
    derniers_articles = Article.query.order_by(Article.created_at.desc()).limit(6).all()
    populaires = Article.query.order_by(Article.views.desc()).limit(5).all()
    sources_en_erreur = (
        Source.query.filter(Source.last_error.isnot(None))
        .order_by(Source.last_fetched_at.desc()).limit(5).all()
    )
    return render_template("admin/dashboard.html", stats=stats,
                           derniers_articles=derniers_articles, populaires=populaires,
                           sources_en_erreur=sources_en_erreur)


# ------------------------------------------------------------------ articles

STATUTS_ARTICLE_FORMULAIRE = ("brouillon", "en_relecture", "programme", "publie")


def _lire_formulaire_article():
    source_url = request.form.get("source_url", "").strip()
    plateforme, erreur_url = valider_url_reseau_social(source_url)

    statut_choisi = request.form.get("status", "brouillon")
    scheduled_at = None
    erreur_scheduled = None
    if statut_choisi == "programme":
        brut = request.form.get("scheduled_at", "").strip()
        if not brut:
            erreur_scheduled = "Choisis une date et une heure pour programmer la publication."
        else:
            try:
                scheduled_at = datetime.strptime(brut, "%Y-%m-%dT%H:%M")
                if scheduled_at <= datetime.utcnow():
                    erreur_scheduled = ("La date de programmation doit être dans le futur "
                                        "(heure UTC).")
            except ValueError:
                erreur_scheduled = "Date de programmation invalide."

    return {
        "title": request.form.get("title", "").strip(),
        "summary": request.form.get("summary", "").strip(),
        "content_html": sanitize_html(request.form.get("content", "")),
        "image_url": request.form.get("image_url", "").strip(),
        "image_credit": request.form.get("image_credit", "").strip(),
        "category_id": request.form.get("category_id", type=int),
        "article_type": request.form.get("article_type", "article"),
        "is_premium": bool(request.form.get("is_premium")),
        "is_featured": bool(request.form.get("is_featured")),
        "status": statut_choisi,
        "scheduled_at": scheduled_at,
        "source_url": source_url or None,
        "source_platform": plateforme,
        "_erreur_source_url": erreur_url,   # préfixe _ : champ interne, jamais écrit en base
        "_erreur_scheduled": erreur_scheduled,
    }


def _valider(donnees):
    erreurs = []
    if len(donnees["title"]) < 5:
        erreurs.append("Le titre doit faire au moins 5 caractères.")
    if len(donnees["summary"]) < 10:
        erreurs.append("Le résumé doit faire au moins 10 caractères.")
    if len(strip_html(donnees["content_html"])) < 30:
        erreurs.append("Le contenu est trop court (30 caractères minimum).")
    if not donnees["category_id"] or not db.session.get(Category, donnees["category_id"]):
        erreurs.append("Choisis une catégorie valide.")
    if donnees["status"] not in STATUTS_ARTICLE_FORMULAIRE:
        erreurs.append("Statut invalide.")
    if donnees["article_type"] not in ARTICLE_TYPES:
        erreurs.append("Type de contenu invalide.")
    if donnees["_erreur_source_url"]:
        erreurs.append(donnees["_erreur_source_url"])
    if donnees["_erreur_scheduled"]:
        erreurs.append(donnees["_erreur_scheduled"])
    return erreurs


def _valider_permissions_redacteur(donnees, article=None):
    """Restrictions supplémentaires pour un simple rédacteur (jamais pour
    modérateur/admin) — voir PLAN_REDACTION.md, §D.

    Le statut ACTUEL de l'article (s'il en a déjà un) reste toléré même
    s'il n'est plus dans la liste normalement permise à un rédacteur : sans
    ça, un rédacteur qui corrige une simple faute de frappe sur un article
    déjà publié par un modérateur se ferait bloquer, ou pire, le
    repasserait accidentellement en brouillon.
    """
    if current_user.is_moderator:
        return []
    erreurs = []
    statut_actuel = article.status if article else None
    if donnees["status"] not in ("brouillon", "en_relecture") and donnees["status"] != statut_actuel:
        erreurs.append("Seul un modérateur peut publier, programmer ou archiver un article.")
    if donnees["is_featured"]:
        erreurs.append("Seul un modérateur peut mettre un article à la Une.")
    return erreurs


def _traiter_image(donnees):
    """Une image envoyée depuis le formulaire remplace l'URL saisie."""
    fichier = request.files.get("image_file")
    if fichier and fichier.filename:
        url, erreur = save_uploaded_image(fichier)
        if erreur:
            return erreur
        donnees["image_url"] = url
    return None


# Champs surveillés pour l'historique — "content" à part car son texte
# complet ne vaut pas la peine d'être dupliqué à chaque modification (voir
# ArticleRevision, models.py). Les autres gardent leur valeur avant/après
# intégrale : ce sont des champs courts par nature.
_CHAMPS_HISTORISES = ("title", "summary", "category_id", "status", "article_type")


def _enregistrer_revisions(article, donnees):
    """Compare l'état actuel de `article` aux nouvelles valeurs de
    `donnees` AVANT toute affectation, et journalise chaque champ changé.
    À appeler avant de modifier `article`, jamais après."""
    for champ in _CHAMPS_HISTORISES:
        ancienne = getattr(article, champ)
        nouvelle = donnees.get(champ if champ != "content" else "content_html")
        if str(ancienne) != str(nouvelle):
            db.session.add(ArticleRevision(
                article_id=article.id, author_id=current_user.id, field_name=champ,
                old_value=str(ancienne) if ancienne is not None else None,
                new_value=str(nouvelle) if nouvelle is not None else None,
            ))

    ancien_contenu = strip_html(article.content or "")
    nouveau_contenu = strip_html(donnees["content_html"] or "")
    if ancien_contenu != nouveau_contenu:
        db.session.add(ArticleRevision(
            article_id=article.id, author_id=current_user.id, field_name="content",
            old_value=f"{len(ancien_contenu)} caractères",
            new_value=f"{len(nouveau_contenu)} caractères",
        ))


@admin_bp.route("/articles")
@login_required
@redacteur_required
def articles():
    statut = request.args.get("statut", "")
    query = Article.query
    if statut in ("publie", "brouillon", "en_relecture", "programme", "archive"):
        query = query.filter_by(status=statut)
    # Un simple rédacteur ne voit que ses propres articles — un modérateur
    # ou admin voit tout, comme avant (voir PLAN_REDACTION.md, §D).
    if not current_user.is_moderator:
        query = query.filter_by(author_id=current_user.id)
    liste = query.order_by(Article.created_at.desc()).all()
    return render_template("admin/articles.html", articles=liste, statut=statut)


@admin_bp.route("/articles/<int:article_id>/archiver", methods=["POST"])
@login_required
@moderator_required
def archive_article(article_id):
    """Retire un article de la circulation publique sans le supprimer ni
    perdre son historique — distinct d'un retour à l'état brouillon, qui
    laisserait croire qu'il n'a jamais été publié."""
    article = Article.query.get_or_404(article_id)
    article.status = "archive"
    db.session.commit()
    flash("Article archivé.", "info")
    return redirect(url_for("admin.articles"))


@admin_bp.route("/articles/publier-programmes", methods=["POST"])
@login_required
@admin_required
def publish_scheduled_now():
    """Version déclenchable depuis l'admin de `flask publish-scheduled` —
    sert à vérifier manuellement que la programmation fonctionne, et de
    filet de sécurité si la tâche planifiée externe ne s'exécute pas."""
    from scheduler import publier_articles_programmes
    n = publier_articles_programmes()
    flash(f"{n} article(s) programmé(s) publié(s).", "success" if n else "info")
    return redirect(url_for("admin.articles"))


@admin_bp.route("/articles/nouveau", methods=["GET", "POST"])
@login_required
@redacteur_required
def new_article():
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        donnees = _lire_formulaire_article()
        erreurs = _valider(donnees) + _valider_permissions_redacteur(donnees)
        erreur_image = _traiter_image(donnees)
        if erreur_image:
            erreurs.append(erreur_image)

        if erreurs:
            for e in erreurs:
                flash(e, "error")
            return render_template("admin/article_form.html", categories=categories,
                                   article=None, form=donnees)

        article = Article(
            title=donnees["title"],
            slug=unique_slug(donnees["title"], Article),
            summary=donnees["summary"],
            content=donnees["content_html"],
            image_url=donnees["image_url"] or None,
            image_credit=donnees["image_credit"] or None,
            category_id=donnees["category_id"],
            article_type=donnees["article_type"],
            author_id=current_user.id,
            is_premium=donnees["is_premium"],
            is_featured=donnees["is_featured"],
            status=donnees["status"],
            scheduled_at=donnees["scheduled_at"],
            # Une URL de réseau social valide classe l'article en
            # conséquence ; sans elle, comportement inchangé ("web").
            source=("reseaux_sociaux" if donnees["source_platform"] else "web"),
            source_url=donnees["source_url"] if donnees["source_platform"] else None,
            source_platform=donnees["source_platform"],
        )
        if article.is_featured:
            Article.query.filter(Article.is_featured.is_(True)).update(
                {"is_featured": False}
            )
        db.session.add(article)
        db.session.commit()
        flash("Article enregistré.", "success")
        return redirect(url_for("admin.articles"))

    return render_template("admin/article_form.html", categories=categories,
                           article=None, form=None)


@admin_bp.route("/articles/<int:article_id>/modifier", methods=["GET", "POST"])
@login_required
@redacteur_required
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)
    # Un simple rédacteur ne modifie jamais l'article de quelqu'un d'autre —
    # un modérateur/admin peut modifier n'importe lequel, comme avant.
    if not current_user.is_moderator and article.author_id != current_user.id:
        abort(403)
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        donnees = _lire_formulaire_article()
        erreurs = _valider(donnees) + _valider_permissions_redacteur(donnees, article)
        erreur_image = _traiter_image(donnees)
        if erreur_image:
            erreurs.append(erreur_image)

        if erreurs:
            for e in erreurs:
                flash(e, "error")
            return render_template("admin/article_form.html", categories=categories,
                                   article=article, form=donnees)

        _enregistrer_revisions(article, donnees)

        if donnees["title"] != article.title:
            article.slug = unique_slug(donnees["title"], Article, exclude_id=article.id)
        article.title = donnees["title"]
        article.summary = donnees["summary"]
        article.content = donnees["content_html"]
        article.image_url = donnees["image_url"] or None
        article.image_credit = donnees["image_credit"] or None
        article.category_id = donnees["category_id"]
        article.article_type = donnees["article_type"]
        article.is_premium = donnees["is_premium"]
        article.status = donnees["status"]
        article.scheduled_at = donnees["scheduled_at"]

        # La provenance d'un article venu de l'agrégateur ou de WhatsApp ne
        # se modifie jamais depuis ce formulaire — seuls "web" et
        # "reseaux_sociaux" peuvent basculer de l'un à l'autre ici, selon
        # que le champ URL est rempli ou vidé.
        if article.source in ("web", "reseaux_sociaux"):
            if donnees["source_platform"]:
                article.source = "reseaux_sociaux"
                article.source_url = donnees["source_url"]
                article.source_platform = donnees["source_platform"]
            else:
                article.source = "web"
                article.source_url = None
                article.source_platform = None

        if donnees["is_featured"] and not article.is_featured:
            Article.query.filter(Article.is_featured.is_(True)).update(
                {"is_featured": False}
            )
        article.is_featured = donnees["is_featured"]

        db.session.commit()
        flash("Article mis à jour.", "success")
        return redirect(url_for("admin.articles"))

    return render_template("admin/article_form.html", categories=categories,
                           article=article, form=None)


# --------------------------------------------------- sources et commentaires
# éditoriaux d'un article (Phase 1 du plan rédaction, voir PLAN_REDACTION.md)

def _peut_gerer_article(article):
    """Modérateur/admin : toujours. Rédacteur : seulement son propre
    article. Centralise cette règle pour les sources, commentaires
    éditoriaux et l'édition elle-même — jamais réimplémentée à la main
    à chaque route, au risque d'un oubli."""
    return current_user.is_moderator or article.author_id == current_user.id


@admin_bp.route("/articles/<int:article_id>/sources", methods=["POST"])
@login_required
@redacteur_required
def add_article_source(article_id):
    article = Article.query.get_or_404(article_id)
    if not _peut_gerer_article(article):
        abort(403)
    nom = request.form.get("nom", "").strip()
    if len(nom) < 2:
        flash("Le nom de la source doit faire au moins 2 caractères.", "error")
        return redirect(url_for("admin.edit_article", article_id=article.id))

    type_source = request.form.get("type_source", "").strip()
    db.session.add(ArticleSource(
        article_id=article.id, nom=nom,
        url=request.form.get("url", "").strip() or None,
        type_source=type_source if type_source in TYPES_SOURCE_ARTICLE else None,
        citation=request.form.get("citation", "").strip() or None,
    ))
    db.session.commit()
    flash("Source ajoutée.", "success")
    return redirect(url_for("admin.edit_article", article_id=article.id))


@admin_bp.route("/articles/<int:article_id>/sources/<int:source_id>/supprimer", methods=["POST"])
@login_required
@redacteur_required
def delete_article_source(article_id, source_id):
    article = Article.query.get_or_404(article_id)
    if not _peut_gerer_article(article):
        abort(403)
    source = ArticleSource.query.filter_by(id=source_id, article_id=article_id).first_or_404()
    db.session.delete(source)
    db.session.commit()
    flash("Source retirée.", "info")
    return redirect(url_for("admin.edit_article", article_id=article_id))


@admin_bp.route("/articles/<int:article_id>/commentaires-editoriaux", methods=["POST"])
@login_required
@redacteur_required
def add_editorial_comment(article_id):
    article = Article.query.get_or_404(article_id)
    if not _peut_gerer_article(article):
        abort(403)
    contenu = request.form.get("content", "").strip()
    if len(contenu) < 2:
        flash("Le commentaire ne peut pas être vide.", "error")
        return redirect(url_for("admin.edit_article", article_id=article.id))

    db.session.add(EditorialComment(
        article_id=article.id, author_id=current_user.id, content=contenu,
    ))
    db.session.commit()
    flash("Commentaire ajouté.", "success")
    return redirect(url_for("admin.edit_article", article_id=article.id))


@admin_bp.route("/articles/<int:article_id>/commentaires-editoriaux/<int:comment_id>/resoudre",
                methods=["POST"])
@login_required
@redacteur_required
def toggle_editorial_comment(article_id, comment_id):
    article = Article.query.get_or_404(article_id)
    if not _peut_gerer_article(article):
        abort(403)
    commentaire = EditorialComment.query.filter_by(
        id=comment_id, article_id=article_id
    ).first_or_404()
    commentaire.resolved = not commentaire.resolved
    db.session.commit()
    return redirect(url_for("admin.edit_article", article_id=article_id))


@admin_bp.route("/articles/<int:article_id>/demander-correction", methods=["POST"])
@login_required
@moderator_required
def request_correction(article_id):
    """Renvoie l'article en brouillon et journalise pourquoi — jamais un
    simple changement de statut muet : sans la raison, le rédacteur n'a
    aucune idée de ce qu'il faut corriger (voir PLAN_REDACTION.md, §Workflow
    éditorial). Réutilise EditorialComment plutôt que d'inventer un
    mécanisme de notification séparé."""
    article = Article.query.get_or_404(article_id)
    contenu = request.form.get("content", "").strip()
    if len(contenu) < 5:
        flash("Explique ce qui doit être corrigé (5 caractères minimum).", "error")
        return redirect(url_for("admin.edit_article", article_id=article.id))

    article.status = "brouillon"
    db.session.add(EditorialComment(
        article_id=article.id, author_id=current_user.id,
        content=f"Correction demandée : {contenu}",
    ))
    db.session.commit()
    flash("Correction demandée — l'article est repassé en brouillon.", "info")
    return redirect(url_for("admin.articles", statut="en_relecture"))


@admin_bp.route("/articles/<int:article_id>/supprimer", methods=["POST"])
@login_required
@moderator_required
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    flash("Article supprimé.", "info")
    return redirect(url_for("admin.articles"))


@admin_bp.route("/upload-image", methods=["POST"])
@login_required
@redacteur_required
def upload_image():
    """Point d'entrée utilisé par l'éditeur pour insérer une image dans le texte."""
    url, erreur = save_uploaded_image(request.files.get("file"))
    if erreur:
        return jsonify({"erreur": erreur}), 400
    return jsonify({"url": url})


# ------------------------------------------------------------- commentaires

@admin_bp.route("/commentaires")
@login_required
@moderator_required
def comments():
    filtre = request.args.get("statut", "en_attente")
    query = Comment.query
    if filtre == "signales":
        query = query.filter_by(reported=True)
    elif filtre in ("en_attente", "approuve", "rejete"):
        query = query.filter_by(status=filtre)
    liste = query.order_by(Comment.created_at.desc()).limit(200).all()
    return render_template("admin/comments.html", comments=liste, filtre=filtre)


@admin_bp.route("/commentaires/<int:comment_id>/statut", methods=["POST"])
@login_required
@moderator_required
def moderate_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    nouveau = request.form.get("status")
    if nouveau in ("approuve", "rejete", "en_attente"):
        comment.status = nouveau
        comment.reported = False
        db.session.add(ModerationLog(
            actor_id=current_user.id, action=f"commentaire_{nouveau}",
            target_type="commentaire", target_id=comment.id,
        ))
        db.session.commit()
        flash("Commentaire mis à jour.", "success")
    return redirect(url_for("admin.comments",
                            statut=request.args.get("statut", "en_attente")))


@admin_bp.route("/commentaires/<int:comment_id>/supprimer", methods=["POST"])
@login_required
@moderator_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.add(ModerationLog(
        actor_id=current_user.id, action="commentaire_supprime",
        target_type="commentaire", target_id=comment.id,
        detail=comment.content[:150],
    ))
    db.session.delete(comment)
    db.session.commit()
    flash("Commentaire supprimé.", "info")
    return redirect(url_for("admin.comments",
                            statut=request.args.get("statut", "en_attente")))


@admin_bp.route("/commentaires/tout-approuver", methods=["POST"])
@login_required
@moderator_required
def approve_all():
    n = Comment.query.filter_by(status="en_attente").update({"status": "approuve"})
    db.session.commit()
    flash(f"{n} commentaire(s) approuvé(s).", "success")
    return redirect(url_for("admin.comments", statut="approuve"))


# ------------------------------------------------------------- utilisateurs

@admin_bp.route("/utilisateurs")
@login_required
@admin_required
def users():
    liste = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=liste)


@admin_bp.route("/utilisateurs/<int:user_id>/role", methods=["POST"])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    nouveau = request.form.get("role")

    if user.id == current_user.id and nouveau != "admin":
        flash("Tu ne peux pas retirer ton propre rôle d'administrateur.", "error")
    elif nouveau in ("user", "redacteur", "moderateur", "admin"):
        user.role = nouveau
        db.session.commit()
        flash(f"Rôle de {user.username} : {nouveau}.", "success")

    return redirect(url_for("admin.users"))


@admin_bp.route("/utilisateurs/<int:user_id>/bannir", methods=["POST"])
@login_required
@admin_required
def toggle_ban(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Tu ne peux pas te bannir toi-même.", "error")
    else:
        user.is_banned = not user.is_banned
        etat = "banni" if user.is_banned else "réintégré"
        db.session.add(ModerationLog(
            actor_id=current_user.id, action=f"utilisateur_{etat}",
            target_type="utilisateur", target_id=user.id, detail=user.username,
        ))
        db.session.commit()
        flash(f"{user.username} est maintenant {etat}.", "success")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------- rubriques

@admin_bp.route("/rubriques", methods=["GET", "POST"])
@login_required
@admin_required
def categories():
    if request.method == "POST":
        nom = request.form.get("name", "").strip()
        if len(nom) < 2:
            flash("Nom de rubrique trop court.", "error")
        elif Category.query.filter_by(name=nom).first():
            flash("Cette rubrique existe déjà.", "error")
        else:
            db.session.add(Category(name=nom, slug=unique_slug(nom, Category)))
            db.session.commit()
            flash("Rubrique créée.", "success")
        return redirect(url_for("admin.categories"))

    liste = Category.query.order_by(Category.name).all()
    return render_template("admin/categories.html", categories=liste)


@admin_bp.route("/rubriques/<int:category_id>/supprimer", methods=["POST"])
@login_required
@admin_required
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    if cat.articles:
        flash(
            f"Impossible de supprimer « {cat.name} » : {len(cat.articles)} article(s) "
            "y sont rattachés. Déplace-les d'abord.",
            "error",
        )
    else:
        db.session.delete(cat)
        db.session.commit()
        flash("Rubrique supprimée.", "info")
    return redirect(url_for("admin.categories"))


# ------------------------------------------------------------ correspondants

@admin_bp.route("/correspondants", methods=["GET", "POST"])
@login_required
@admin_required
def correspondents():
    if request.method == "POST":
        nom = request.form.get("name", "").strip()
        numero = normalize_phone(request.form.get("phone", ""))

        if len(nom) < 2:
            flash("Nom trop court.", "error")
        elif not numero:
            flash("Numéro de téléphone invalide.", "error")
        elif Correspondent.query.filter_by(phone_number=numero).first():
            flash("Ce numéro est déjà enregistré.", "error")
        else:
            import secrets
            # Compte "muet" utilisé uniquement pour attribuer la signature des
            # articles : le correspondant ne se connecte jamais avec, il publie
            # exclusivement par WhatsApp. Mot de passe aléatoire, jamais transmis.
            identifiant = unique_slug(nom, User, field="username")
            compte = User(
                username=identifiant,
                email=f"{identifiant}@correspondants.local",
                role="user",
            )
            compte.set_password(secrets.token_urlsafe(24))
            db.session.add(compte)
            db.session.flush()

            db.session.add(Correspondent(name=nom, phone_number=numero, user_id=compte.id))
            db.session.commit()
            flash(f"Correspondant « {nom} » ajouté ({numero}).", "success")

        return redirect(url_for("admin.correspondents"))

    liste = Correspondent.query.order_by(Correspondent.created_at.desc()).all()
    return render_template("admin/correspondents.html", correspondents=liste)


@admin_bp.route("/correspondants/<int:correspondent_id>/statut", methods=["POST"])
@login_required
@admin_required
def toggle_correspondent(correspondent_id):
    correspondant = Correspondent.query.get_or_404(correspondent_id)
    correspondant.is_active = not correspondant.is_active
    db.session.commit()
    etat = "actif" if correspondant.is_active else "inactif"
    flash(f"{correspondant.name} est maintenant {etat}.", "success")
    return redirect(url_for("admin.correspondents"))


@admin_bp.route("/correspondants/<int:correspondent_id>/supprimer", methods=["POST"])
@login_required
@admin_required
def delete_correspondent(correspondent_id):
    correspondant = Correspondent.query.get_or_404(correspondent_id)
    # Les articles déjà créés restent en base, signés par le compte existant ;
    # seul le droit de soumettre de nouveaux brouillons est retiré.
    db.session.delete(correspondant)
    db.session.commit()
    flash("Correspondant supprimé. Ses articles déjà publiés restent en ligne.", "info")
    return redirect(url_for("admin.correspondents"))


# ---------------------------------------------------------------- sources

def _lire_formulaire_source():
    return {
        "name": request.form.get("name", "").strip(),
        "site_url": request.form.get("site_url", "").strip(),
        "feed_url": request.form.get("feed_url", "").strip(),
        "country": request.form.get("country", "").strip() or None,
        "trust_level": request.form.get("trust_level", type=int) or 50,
        "fetch_frequency_minutes": request.form.get("fetch_frequency_minutes", type=int) or 60,
        "keywords_include": request.form.get("keywords_include", "").strip() or None,
        "keywords_exclude": request.form.get("keywords_exclude", "").strip() or None,
        "category_id": request.form.get("category_id", type=int) or None,
        "compliance_checked": bool(request.form.get("compliance_checked")),
        "compliance_notes": request.form.get("compliance_notes", "").strip() or None,
        # Une source inactive par défaut : l'activation est un choix
        # explicite, jamais un oubli de décochage.
        "is_active": bool(request.form.get("is_active")),
        "source_category": request.form.get("source_category", "media"),
        "content_mode": request.form.get("content_mode", "extrait"),
        "content_license_justification":
            request.form.get("content_license_justification", "").strip() or None,
    }


def _valider_source(donnees, source_existante=None):
    erreurs = []
    if len(donnees["name"]) < 2:
        erreurs.append("Le nom de la source doit faire au moins 2 caractères.")
    if not donnees["site_url"].startswith(("http://", "https://")):
        erreurs.append("L'URL du site doit commencer par http:// ou https://.")
    if not donnees["feed_url"].startswith(("http://", "https://")):
        erreurs.append("L'URL du flux doit commencer par http:// ou https://.")
    if not (0 <= donnees["trust_level"] <= 100):
        erreurs.append("Le niveau de confiance doit être compris entre 0 et 100.")
    if donnees["fetch_frequency_minutes"] < 5:
        erreurs.append("La fréquence de collecte ne peut pas être inférieure à 5 minutes — "
                       "au-delà, on sollicite le site source pour rien.")
    if donnees["is_active"] and not donnees["compliance_checked"]:
        erreurs.append(
            "Impossible d'activer une source sans avoir coché la vérification "
            "de conformité (robots.txt / CGU). Voir PLAN_AGREGATEUR.md."
        )

    if donnees["source_category"] not in ("media", "gouvernemental", "institutionnel"):
        erreurs.append("Classification de source invalide.")
    if donnees["content_mode"] not in ("extrait", "integral"):
        erreurs.append("Mode de contenu invalide.")
    if donnees["content_mode"] == "integral":
        if donnees["source_category"] == "media":
            erreurs.append(
                "Le mode intégral n'est possible que pour une source classée "
                "gouvernementale ou institutionnelle — pas pour un média. "
                "Reste sur « extrait » pour une source de presse."
            )
        justification = donnees["content_license_justification"] or ""
        if len(justification) < 20:
            erreurs.append(
                "Le mode intégral exige une justification écrite d'au moins 20 "
                "caractères : accord, conditions de syndication publiées, ou "
                "communiqué qui se déclare lui-même libre de reproduction."
            )

    query = Source.query.filter_by(name=donnees["name"])
    if source_existante is not None:
        query = query.filter(Source.id != source_existante.id)
    if query.first():
        erreurs.append("Une source porte déjà ce nom.")

    return erreurs


@admin_bp.route("/sources")
@login_required
@admin_required
def sources():
    liste = Source.query.order_by(Source.name).all()
    compteurs = dict(
        db.session.query(CollectedArticle.source_id, db.func.count(CollectedArticle.id))
        .group_by(CollectedArticle.source_id).all()
    )
    return render_template("admin/sources.html", sources=liste, compteurs=compteurs)


@admin_bp.route("/sources/nouvelle", methods=["GET", "POST"])
@login_required
@admin_required
def new_source():
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        donnees = _lire_formulaire_source()
        erreurs = _valider_source(donnees)

        if erreurs:
            for e in erreurs:
                flash(e, "error")
            return render_template("admin/source_form.html", categories=categories,
                                   source=None, form=donnees)

        db.session.add(Source(**donnees))
        db.session.commit()
        flash(f"Source « {donnees['name']} » créée.", "success")
        return redirect(url_for("admin.sources"))

    return render_template("admin/source_form.html", categories=categories,
                           source=None, form=None)


@admin_bp.route("/sources/<int:source_id>/modifier", methods=["GET", "POST"])
@login_required
@admin_required
def edit_source(source_id):
    source = Source.query.get_or_404(source_id)
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        donnees = _lire_formulaire_source()
        erreurs = _valider_source(donnees, source_existante=source)

        if erreurs:
            for e in erreurs:
                flash(e, "error")
            return render_template("admin/source_form.html", categories=categories,
                                   source=source, form=donnees)

        for champ, valeur in donnees.items():
            setattr(source, champ, valeur)
        db.session.commit()
        flash("Source mise à jour.", "success")
        return redirect(url_for("admin.sources"))

    return render_template("admin/source_form.html", categories=categories,
                           source=source, form=None)


@admin_bp.route("/sources/<int:source_id>/supprimer", methods=["POST"])
@login_required
@admin_required
def delete_source(source_id):
    source = Source.query.get_or_404(source_id)
    db.session.delete(source)
    db.session.commit()
    flash("Source supprimée. Les articles déjà publiés à partir de celle-ci restent en ligne.", "info")
    return redirect(url_for("admin.sources"))


@admin_bp.route("/sources/<int:source_id>/tester", methods=["POST"])
@login_required
@admin_required
def test_source(source_id):
    """Lit les premiers items du flux sans rien enregistrer — sert à valider
    la configuration avant d'activer la collecte pour de bon."""
    source = Source.query.get_or_404(source_id)
    try:
        items = feed_client.fetch_feed(source.feed_url)
    except feed_client.ErreurFlux as exc:
        return jsonify({"erreur": str(exc)}), 502

    return jsonify({
        "nombre_items": len(items),
        "apercu": [
            {"title": i["title"], "url": i["url"], "published_at":
             i["published_at"].isoformat() if i["published_at"] else None}
            for i in items[:5]
        ],
    })


@admin_bp.route("/sources/<int:source_id>/collecter", methods=["POST"])
@login_required
@admin_required
def collect_now(source_id):
    """Collecte immédiatement une seule source et ENREGISTRE les résultats
    (contrairement à /tester, qui ne fait que prévisualiser).

    Existe pour les hébergeurs où la commande `flask collect-sources` ne
    peut pas être programmée en tâche de fond (pas d'accès shell/cron
    disponible) — un déclenchement manuel depuis l'admin reste possible.
    Régle par la même occasion le sujet et le score des nouveaux articles,
    comme le ferait un cycle complet de `flask collect-sources`.
    """
    source = Source.query.get_or_404(source_id)
    if not source.is_active or not source.compliance_checked:
        flash("Cette source doit être active et sa conformité vérifiée avant "
             "de pouvoir être collectée.", "error")
        return redirect(url_for("admin.sources"))

    resultat = collector.collecter_source(source)

    if resultat["statut"] == "ok" and resultat["nouveaux"] > 0:
        topic_matcher.rattacher_sujets()
        scoring_engine.noter_articles()
        flash(f"{resultat['nouveaux']} nouvel(aux) article(s) collecté(s) depuis "
             f"« {source.name} ».", "success")
    elif resultat["statut"] == "ok":
        flash(f"Collecte effectuée — aucun nouvel article depuis « {source.name} » "
             "(tout est déjà connu).", "info")
    else:
        flash(f"Échec de la collecte pour « {source.name} » : {resultat['erreur']}", "error")

    return redirect(url_for("admin.sources"))


# ---------------------------------------------------------------- scoring

def _lire_formulaire_scoring():
    def _f(nom, defaut):
        return request.form.get(nom, type=float) if request.form.get(nom) else defaut

    return {
        "weight_importance": _f("weight_importance", 0.30),
        "weight_freshness": _f("weight_freshness", 0.20),
        "weight_popularity": _f("weight_popularity", 0.20),
        "weight_relevance": _f("weight_relevance", 0.20),
        "weight_trust": _f("weight_trust", 0.10),
        "threshold_high": _f("threshold_high", 75.0),
        "threshold_medium": _f("threshold_medium", 50.0),
        "threshold_low": _f("threshold_low", 25.0),
        "importance_keywords": request.form.get("importance_keywords", "").strip(),
        "topic_similarity_threshold": _f("topic_similarity_threshold", 70.0),
    }


def _valider_scoring(donnees):
    erreurs = []
    somme = (donnees["weight_importance"] + donnees["weight_freshness"]
            + donnees["weight_popularity"] + donnees["weight_relevance"]
            + donnees["weight_trust"])
    if abs(somme - 1.0) > 0.01:
        erreurs.append(f"Les cinq pondérations doivent sommer à 1.0 (actuellement {somme:.2f}).")
    for nom in ("weight_importance", "weight_freshness", "weight_popularity",
               "weight_relevance", "weight_trust"):
        if donnees[nom] < 0:
            erreurs.append("Aucune pondération ne peut être négative.")
            break
    if not (donnees["threshold_high"] > donnees["threshold_medium"] > donnees["threshold_low"]):
        erreurs.append("Les seuils doivent être strictement décroissants : "
                       "rouge > orange > jaune.")
    if not donnees["importance_keywords"]:
        erreurs.append("La liste des mots-clés d'importance ne peut pas être vide.")
    return erreurs


@admin_bp.route("/scoring", methods=["GET", "POST"])
@login_required
@admin_required
def scoring():
    """Réglage des pondérations, avec aperçu en direct sur les articles déjà
    collectés — voir l'effet d'un changement avant de l'appliquer pour de
    bon, plutôt que de régler à l'aveugle."""
    config_active = ScoringConfig.get_active()
    echantillon = (
        CollectedArticle.query.order_by(CollectedArticle.collected_at.desc())
        .limit(15).all()
    )

    donnees = None
    erreurs = []

    if request.method == "POST":
        donnees = _lire_formulaire_scoring()
        erreurs = _valider_scoring(donnees)

        if not erreurs and request.form.get("action") == "enregistrer":
            nouvelle_config = ScoringConfig(**donnees)
            db.session.add(nouvelle_config)
            db.session.commit()
            nb = scoring_engine.noter_articles()
            flash(f"Pondérations enregistrées — {nb} article(s) re-noté(s).", "success")
            return redirect(url_for("admin.scoring"))

        if erreurs:
            for e in erreurs:
                flash(e, "error")

    config_pour_apercu = ScoringConfig(**donnees) if (donnees and not erreurs) else config_active

    apercus = []
    for article in echantillon:
        detail = scoring_engine.apercu_score(article, config_pour_apercu)
        apercus.append((article, detail))
    apercus.sort(key=lambda pair: pair[1]["total"], reverse=True)

    return render_template("admin/scoring.html", config=config_active,
                           form=donnees, apercus=apercus,
                           config_pour_apercu=config_pour_apercu)


# --------------------------------------------------------- file d'agrégation

def _construire_brouillon_depuis_collecte(collecte):
    """Construit le contenu HTML initial du brouillon à partir d'un article
    collecté.

    Deux cas :
    - Source en mode "extrait" (l'immense majorité) : un extrait — jamais le
      texte intégral (feed_client le limite à 400 caractères, Mode 1
      uniquement, voir PLAN_AGREGATEUR.md §0) — suivi d'une attribution
      « Source : nom, lien ».
    - Source en mode "integral" (gouvernementale/institutionnelle, justifiée
      — voir Source.content_license_justification) ET contenu intégral
      effectivement fourni par CET item précis : le texte complet, suivi
      d'une attribution qui le nomme explicitement comme un communiqué
      repris intégralement, pas comme un article agrégé ordinaire.

    Dans les deux cas, passé par sanitize_html() avant stockage — même si
    feed_client.py l'a déjà fait à l'extraction, la défense en profondeur ne
    coûte rien ici et un contenu qui vient d'un flux RSS externe reste, par
    principe, une entrée non fiable.
    """
    source = collecte.source
    morceaux = []

    if source.content_mode == "integral" and collecte.content_full:
        morceaux.append(collecte.content_full)
        morceaux.append(
            '<p><em>Communiqué officiel repris intégralement — source : '
            '<a href="{url}" target="_blank" rel="noopener noreferrer">{nom}</a></em></p>'
            .format(
                url=html_module.escape(collecte.external_url, quote=True),
                nom=html_module.escape(source.name),
            )
        )
    else:
        if collecte.excerpt:
            morceaux.append(f"<p>{html_module.escape(collecte.excerpt)}</p>")
        morceaux.append(
            '<p><em>Source : <a href="{url}" target="_blank" rel="noopener noreferrer">{nom}</a></em></p>'
            .format(
                url=html_module.escape(collecte.external_url, quote=True),
                nom=html_module.escape(source.name),
            )
        )

    return sanitize_html("".join(morceaux))


@admin_bp.route("/agregation")
@login_required
@admin_required
def aggregation_queue():
    statut = request.args.get("statut", "nouveau")
    topic_id = request.args.get("topic_id", type=int)

    query = CollectedArticle.query
    if statut in COLLECTED_STATUSES:
        query = query.filter_by(status=statut)
    if topic_id:
        query = query.filter_by(topic_id=topic_id)

    articles = query.order_by(CollectedArticle.score_total.desc()).limit(100).all()

    sujets_actifs = (
        Topic.query.filter(Topic.sources_count >= 2)
        .order_by(Topic.first_seen_at.desc()).limit(20).all()
    )
    topic_filtre = db.session.get(Topic, topic_id) if topic_id else None

    return render_template(
        "admin/aggregation.html", articles=articles, statut=statut,
        topic_id=topic_id, topic_filtre=topic_filtre, sujets_actifs=sujets_actifs,
    )


@admin_bp.route("/agregation/<int:collected_id>/accepter", methods=["POST"])
@login_required
@admin_required
def accept_collected(collected_id):
    collecte = CollectedArticle.query.get_or_404(collected_id)

    if collecte.status == "accepte":
        flash("Cet article a déjà été accepté.", "info")
        return redirect(url_for("admin.aggregation_queue"))

    if not collecte.title or not collecte.title.strip():
        flash("Impossible d'accepter : cet article n'a pas de titre exploitable.", "error")
        return redirect(url_for("admin.aggregation_queue"))

    categorie = (
        (db.session.get(Category, collecte.source.category_id)
         if collecte.source.category_id else None)
        or Category.query.order_by(Category.name).first()
    )
    if not categorie:
        flash("Aucune rubrique n'existe encore — crée-en une avant d'accepter un article.",
              "error")
        return redirect(url_for("admin.aggregation_queue"))

    resume = (collecte.excerpt or collecte.title)[:400].strip()
    if len(resume) < 10:
        resume = f"{collecte.title} — repéré via {collecte.source.name}."[:400]

    article = Article(
        title=collecte.title[:200],
        slug=unique_slug(collecte.title, Article),
        summary=resume,
        content=_construire_brouillon_depuis_collecte(collecte),
        image_url=collecte.image_url,
        image_credit=(f"Source : {collecte.source.name}" if collecte.image_url else None),
        category_id=categorie.id,
        author_id=current_user.id,
        status="brouillon",
        source="agregateur",
    )
    db.session.add(article)
    db.session.flush()          # pour obtenir article.id avant affectation

    collecte.status = "accepte"
    collecte.published_article_id = article.id
    db.session.commit()

    flash(f"Brouillon créé à partir de « {collecte.source.name} » — "
         "relis et complète avant de publier.", "success")
    return redirect(url_for("admin.edit_article", article_id=article.id))


@admin_bp.route("/agregation/<int:collected_id>/statut", methods=["POST"])
@login_required
@admin_required
def moderate_collected(collected_id):
    collecte = CollectedArticle.query.get_or_404(collected_id)
    nouveau_statut = request.form.get("status")
    if nouveau_statut in ("nouveau", "rejete", "archive"):
        collecte.status = nouveau_statut
        db.session.commit()
        flash("Statut mis à jour.", "success")
    return redirect(url_for("admin.aggregation_queue",
                            statut=request.args.get("statut", "nouveau")))


# ------------------------------------------------------ journal de modération

@admin_bp.route("/journal")
@login_required
@moderator_required
def moderation_log():
    entrees = (
        ModerationLog.query.order_by(ModerationLog.created_at.desc())
        .limit(200).all()
    )
    return render_template("admin/journal.html", entrees=entrees)


# --------------------------------------------------------------- pulaar

@admin_bp.route("/pulaar")
@login_required
@moderator_required
def pulaar_dashboard():
    return render_template(
        "admin/pulaar_dashboard.html",
        nb_termes=PulaarTerm.query.count(),
        nb_valides=PulaarTerm.query.filter_by(status="validated").count(),
        nb_propositions=PulaarProposal.query.filter_by(status="en_attente").count(),
        nb_domaines=PulaarDomain.query.count(),
    )


@admin_bp.route("/pulaar/domaines", methods=["GET", "POST"])
@login_required
@moderator_required
def pulaar_domains():
    if request.method == "POST":
        nom = request.form.get("name", "").strip()
        if len(nom) < 2:
            flash("Le nom du domaine doit faire au moins 2 caractères.", "error")
        elif PulaarDomain.query.filter_by(name=nom).first():
            flash("Ce domaine existe déjà.", "error")
        else:
            db.session.add(PulaarDomain(name=nom, slug=unique_slug(nom, PulaarDomain)))
            db.session.commit()
            flash(f"Domaine « {nom} » créé.", "success")
        return redirect(url_for("admin.pulaar_domains"))

    domaines = PulaarDomain.query.order_by(PulaarDomain.name).all()
    return render_template("admin/pulaar_domains.html", domaines=domaines)


@admin_bp.route("/pulaar/termes")
@login_required
@moderator_required
def pulaar_terms():
    statut = request.args.get("statut", "")
    query = PulaarTerm.query
    if statut in PULAAR_TERM_STATUTS:
        query = query.filter_by(status=statut)
    termes = query.order_by(PulaarTerm.lemma).all()
    return render_template("admin/pulaar_terms.html", termes=termes, statut=statut)


@admin_bp.route("/pulaar/termes/nouveau", methods=["GET", "POST"])
@login_required
@moderator_required
def new_pulaar_term():
    domaines = PulaarDomain.query.order_by(PulaarDomain.name).all()
    sources = PulaarSource.query.order_by(PulaarSource.name).all()

    if request.method == "POST":
        lemme = request.form.get("lemma", "").strip()
        def_fr = request.form.get("definition_fr", "").strip()
        source_id = request.form.get("source_id", type=int)
        erreurs = []
        if len(lemme) < 1:
            erreurs.append("Le terme ne peut pas être vide.")
        if len(def_fr) < 3:
            erreurs.append("La définition en français doit faire au moins 3 caractères.")
        if not source_id or not db.session.get(PulaarSource, source_id):
            erreurs.append("Choisis une source valide — un terme n'existe jamais sans provenance.")

        if erreurs:
            for e in erreurs:
                flash(e, "error")
            return render_template("admin/pulaar_term_form.html", domaines=domaines,
                                   sources=sources, terme=None)

        domain_id = request.form.get("domain_id", type=int)
        t = PulaarTerm(
            lemma=lemme, slug=unique_slug(lemme, PulaarTerm),
            part_of_speech=request.form.get("part_of_speech", "").strip() or None,
            domain_id=domain_id if domain_id else None,
            source_id=source_id,
        )
        db.session.add(t)
        db.session.flush()  # pour obtenir t.id avant la définition liée
        db.session.add(PulaarDefinition(term_id=t.id, lang="fr", text=def_fr))
        def_en = request.form.get("definition_en", "").strip()
        if def_en:
            db.session.add(PulaarDefinition(term_id=t.id, lang="en", text=def_en))
        db.session.commit()
        flash(f"Terme « {lemme} » créé.", "success")
        return redirect(url_for("admin.pulaar_terms"))

    return render_template("admin/pulaar_term_form.html", domaines=domaines,
                           sources=sources, terme=None)


@admin_bp.route("/pulaar/termes/<int:term_id>/valider", methods=["POST"])
@login_required
@moderator_required
def validate_pulaar_term(term_id):
    """Bascule entre "documented" et "validated" — jamais l'inverse par
    défaut : un terme reste "documented" tant qu'un humain n'a pas
    explicitement confirmé sa justesse linguistique."""
    t = PulaarTerm.query.get_or_404(term_id)
    t.status = "validated" if t.status != "validated" else "documented"
    db.session.commit()
    return redirect(url_for("admin.pulaar_terms"))


@admin_bp.route("/pulaar/termes/<int:term_id>/supprimer", methods=["POST"])
@login_required
@moderator_required
def delete_pulaar_term(term_id):
    t = PulaarTerm.query.get_or_404(term_id)
    db.session.delete(t)
    db.session.commit()
    flash("Terme supprimé.", "info")
    return redirect(url_for("admin.pulaar_terms"))


@admin_bp.route("/pulaar/propositions")
@login_required
@moderator_required
def pulaar_proposals():
    statut = request.args.get("statut", "en_attente")
    query = PulaarProposal.query
    if statut in PULAAR_PROPOSAL_STATUTS:
        query = query.filter_by(status=statut)
    propositions = query.order_by(PulaarProposal.created_at.desc()).all()
    return render_template("admin/pulaar_proposals.html", propositions=propositions, statut=statut)


def _source_contribution_communautaire():
    """Une seule ligne PulaarSource réutilisée pour toute proposition
    acceptée — plutôt qu'une ligne par acceptation, qui bruiterait la
    liste des sources sans rien apporter de plus."""
    source = PulaarSource.query.filter_by(method="contribution").first()
    if not source:
        source = PulaarSource(
            name="Contribution communautaire", method="contribution",
            license="Kaloum24 — vérifié par la modération avant publication",
        )
        db.session.add(source)
        db.session.flush()
    return source


@admin_bp.route("/pulaar/propositions/<int:proposal_id>/accepter", methods=["POST"])
@login_required
@moderator_required
def accept_pulaar_proposal(proposal_id):
    p = PulaarProposal.query.get_or_404(proposal_id)
    if p.status != "en_attente":
        flash("Cette proposition a déjà été traitée.", "error")
        return redirect(url_for("admin.pulaar_proposals"))

    source = _source_contribution_communautaire()
    t = PulaarTerm(
        lemma=p.term_lemma, slug=unique_slug(p.term_lemma, PulaarTerm),
        domain_id=p.domain_id, source_id=source.id, status="documented",
    )
    db.session.add(t)
    db.session.flush()
    db.session.add(PulaarDefinition(term_id=t.id, lang="fr", text=p.definition_fr))
    p.status = "valide"
    db.session.commit()
    flash(f"Proposition acceptée — « {p.term_lemma} » ajouté au dictionnaire.", "success")
    return redirect(url_for("admin.pulaar_proposals"))


@admin_bp.route("/pulaar/propositions/<int:proposal_id>/rejeter", methods=["POST"])
@login_required
@moderator_required
def reject_pulaar_proposal(proposal_id):
    p = PulaarProposal.query.get_or_404(proposal_id)
    if p.status != "en_attente":
        flash("Cette proposition a déjà été traitée.", "error")
        return redirect(url_for("admin.pulaar_proposals"))
    p.status = "rejete"
    db.session.commit()
    flash("Proposition rejetée.", "info")
    return redirect(url_for("admin.pulaar_proposals"))
