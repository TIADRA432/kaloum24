from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
    Response, current_app, jsonify,
)
from flask_login import current_user, login_required

from extensions import db, limiter
import comment_spam
import view_counter
from models import Article, Category, Comment, ModerationLog

main_bp = Blueprint("main", __name__)


def _published():
    return Article.query.filter_by(status="publie")


@main_bp.route("/")
def home():
    hero = (
        _published().filter_by(is_featured=True).order_by(Article.created_at.desc()).first()
        or _published().order_by(Article.created_at.desc()).first()
    )
    secondary = (
        _published().filter(Article.id != (hero.id if hero else 0))
        .order_by(Article.created_at.desc()).limit(4).all()
    )
    exclude_ids = [a.id for a in ([hero] if hero else []) + secondary]

    latest_q = _published()
    if exclude_ids:
        latest_q = latest_q.filter(~Article.id.in_(exclude_ids))
    latest = latest_q.order_by(Article.created_at.desc()).limit(9).all()

    most_read = _published().order_by(Article.views.desc()).limit(6).all()

    # Une sélection par rubrique, pour donner du relief à la page d'accueil.
    par_rubrique = []
    for cat in Category.query.order_by(Category.name).all():
        articles = (
            _published().filter_by(category_id=cat.id)
            .order_by(Article.created_at.desc()).limit(4).all()
        )
        if len(articles) >= 2:
            par_rubrique.append((cat, articles))

    return render_template(
        "index.html", hero=hero, secondary=secondary, latest=latest,
        most_read=most_read, par_rubrique=par_rubrique[:3],
    )


@main_bp.route("/categorie/<slug>")
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    pagination = (
        Article.query.filter_by(category_id=cat.id, status="publie")
        .order_by(Article.created_at.desc())
        .paginate(page=page, per_page=current_app.config["ARTICLES_PER_PAGE"],
                  error_out=False)
    )
    most_read = _published().order_by(Article.views.desc()).limit(6).all()
    return render_template("category.html", category=cat, pagination=pagination,
                           most_read=most_read)


@main_bp.route("/article/<slug>")
def article_detail(slug):
    article = Article.query.filter_by(slug=slug).first_or_404()
    if article.status != "publie" and not (
        current_user.is_authenticated and current_user.is_moderator
    ):
        abort(404)

    # Une vue par session et par article, pour éviter de gonfler le compteur
    # à chaque rechargement. Le comptage est tamponné en mémoire (voir
    # view_counter.py) : sans cela, chaque lecture produirait une écriture en
    # base, ce qui sature SQLite dès qu'un article est partagé largement.
    from flask import session
    vus = session.get("vus", [])
    if article.id not in vus:
        view_counter.enregistrer_vue(current_app, article.id)
        session["vus"] = (vus + [article.id])[-80:]

    # Total affiché = ce qui est en base + ce qui n'y est pas encore écrit.
    vues_affichees = (article.views or 0) + view_counter.vues_en_attente(article.id)

    is_locked = article.is_premium and not (
        current_user.is_authenticated and current_user.is_subscriber
    )

    similaires = (
        _published().filter(Article.category_id == article.category_id)
        .filter(Article.id != article.id)
        .order_by(Article.created_at.desc()).limit(4).all()
    )
    if len(similaires) < 4:
        complement = (
            _published().filter(Article.id != article.id)
            .filter(~Article.id.in_([a.id for a in similaires] or [0]))
            .order_by(Article.views.desc()).limit(4 - len(similaires)).all()
        )
        similaires += complement

    return render_template("article.html", article=article, is_locked=is_locked,
                           similaires=similaires, vues_affichees=vues_affichees)


@main_bp.route("/article/<slug>/commentaire", methods=["POST"])
@login_required
@limiter.limit(lambda: current_app.config["RATELIMIT_COMMENT"])
def post_comment(slug):
    article = Article.query.filter_by(slug=slug).first_or_404()

    if current_user.is_banned:
        flash("Ton compte ne peut plus commenter. Contacte la rédaction.", "error")
        return redirect(url_for("main.article_detail", slug=slug) + "#commentaires")

    content = request.form.get("content", "").strip()
    parent_id = request.form.get("parent_id", type=int)

    if not content:
        flash("Le commentaire ne peut pas être vide.", "error")
    elif len(content) > 2000:
        flash("Commentaire trop long (2000 caractères maximum).", "error")
    else:
        parent = db.session.get(Comment, parent_id) if parent_id else None
        if parent and parent.article_id != article.id:
            parent = None                      # réponse à un commentaire d'un autre article

        suspect, raisons = comment_spam.evaluer(
            content, current_app.config, user_id=current_user.id, model_comment=Comment
        )

        if current_app.config["COMMENT_AUTO_APPROVE"] and not suspect:
            statut = "approuve"
            message = "Commentaire publié."
        else:
            statut = "en_attente"
            message = "Commentaire envoyé — il apparaîtra après validation par la modération."

        comment = Comment(
            content=content, article_id=article.id, user_id=current_user.id,
            parent_id=parent.id if parent else None, status=statut,
        )
        db.session.add(comment)
        db.session.flush()

        if suspect:
            db.session.add(ModerationLog(
                actor_id=None, action="commentaire_signale_automatiquement",
                target_type="commentaire", target_id=comment.id,
                detail="; ".join(raisons)[:300],
            ))
        elif statut == "approuve":
            db.session.add(ModerationLog(
                actor_id=None, action="commentaire_auto_approuve",
                target_type="commentaire", target_id=comment.id,
                detail="Publié automatiquement (COMMENT_AUTO_APPROVE actif, aucun signal suspect).",
            ))

        db.session.commit()
        flash(message, "success")

    return redirect(url_for("main.article_detail", slug=slug) + "#commentaires")


@main_bp.route("/commentaire/<int:comment_id>/signaler", methods=["POST"])
@login_required
def report_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.reported = True
    db.session.add(ModerationLog(
        actor_id=current_user.id, action="commentaire_signale_par_lecteur",
        target_type="commentaire", target_id=comment.id,
    ))
    db.session.commit()
    flash("Commentaire signalé à la modération. Merci.", "info")
    return redirect(
        url_for("main.article_detail", slug=comment.article.slug) + "#commentaires"
    )


@main_bp.route("/recherche")
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%{q}%"
        results = (
            Article.query.filter(Article.status == "publie")
            .filter(db.or_(Article.title.ilike(like), Article.summary.ilike(like),
                           Article.content.ilike(like)))
            .order_by(Article.created_at.desc()).limit(40).all()
        )
    return render_template("search.html", query=q, results=results)


# ---------------------------------------------------------------- SEO / flux

@main_bp.route("/rss.xml")
def rss():
    articles = _published().order_by(Article.created_at.desc()).limit(30).all()
    xml = render_template("feed.xml", articles=articles)
    return Response(xml, mimetype="application/rss+xml")


@main_bp.route("/sitemap.xml")
def sitemap():
    articles = _published().order_by(Article.created_at.desc()).limit(2000).all()
    categories = Category.query.all()
    xml = render_template("sitemap.xml", articles=articles, categories=categories)
    return Response(xml, mimetype="application/xml")


@main_bp.route("/robots.txt")
def robots():
    site = current_app.config["SITE_URL"].rstrip("/")
    lignes = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /compte",
        "Disallow: /recherche",
        "",
        f"Sitemap: {site}/sitemap.xml",
    ]
    return Response("\n".join(lignes), mimetype="text/plain")


# ---------------------------------------------------------------- météo

@main_bp.route("/api/meteo")
def weather():
    """Relais vers Open-Meteo (gratuit, sans clé), avec cache en mémoire.

    Passer par le serveur évite d'exposer l'appel côté client et permet de
    mutualiser le cache entre tous les visiteurs.
    """
    import json
    import time
    import urllib.request

    if not current_app.config["WEATHER_ENABLED"]:
        return jsonify({"disponible": False}), 404

    cache = current_app.extensions.setdefault("meteo_cache", {})
    if cache.get("expire", 0) > time.time():
        return jsonify(cache["data"])

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={current_app.config['WEATHER_LAT']}"
        f"&longitude={current_app.config['WEATHER_LON']}"
        "&current=temperature_2m,weather_code"
        f"&timezone={current_app.config['WEATHER_TIMEZONE']}"
    )
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            brut = json.loads(resp.read().decode())
        data = {
            "disponible": True,
            "ville": current_app.config["WEATHER_CITY"],
            "temperature": round(brut["current"]["temperature_2m"]),
            "code": brut["current"]["weather_code"],
        }
    except Exception as exc:
        current_app.logger.warning("Météo indisponible : %s", exc)
        return jsonify({"disponible": False}), 503

    cache["data"] = data
    cache["expire"] = time.time() + 1800        # 30 minutes
    return jsonify(data)


@main_bp.route("/sante")
@limiter.exempt
def sante():
    """Point de contrôle pour la surveillance externe (UptimeRobot, etc.).

    Vérifie que l'application répond ET que la base est joignable — un site
    qui renvoie 200 alors que sa base est tombée n'est pas « en ligne ».
    """
    from sqlalchemy import text as sql_text

    try:
        db.session.execute(sql_text("SELECT 1"))
        return jsonify({"statut": "ok", "base": "ok"}), 200
    except Exception as exc:
        current_app.logger.error("Contrôle de santé : base injoignable (%s)", exc)
        return jsonify({"statut": "degrade", "base": "injoignable"}), 503
