from datetime import datetime

from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

ROLES = ("user", "moderateur", "admin")
ARTICLE_STATUSES = ("brouillon", "publie")
COMMENT_STATUSES = ("en_attente", "approuve", "rejete")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_subscriber = db.Column(db.Boolean, nullable=False, default=False)
    is_banned = db.Column(db.Boolean, nullable=False, default=False)
    stripe_customer_id = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    articles = db.relationship("Article", back_populates="author")
    comments = db.relationship("Comment", back_populates="user")
    subscription = db.relationship("Subscription", back_populates="user", uselist=False)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_moderator(self):
        return self.role in ("admin", "moderateur")

    @property
    def is_redacteur_or_above(self):
        """Peut accéder à l'espace de rédaction (créer/modifier SES
        propres articles) — mais pas forcément publier ou modifier ceux
        des autres, contrairement à is_moderator. Voir PLAN_REDACTION.md,
        §D, et blueprints/admin.py pour l'application de cette restriction."""
        return self.role in ("admin", "moderateur", "redacteur")

    # --- Réinitialisation de mot de passe (jeton signé, sans stockage en base) ---

    def reset_token(self):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="reset-mdp")
        # Le hash actuel entre dans le jeton : changer de mot de passe invalide
        # automatiquement tous les liens déjà envoyés.
        return s.dumps({"uid": self.id, "h": self.password_hash[-16:]})

    @staticmethod
    def verify_reset_token(token):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="reset-mdp")
        try:
            data = s.loads(token, max_age=current_app.config["RESET_TOKEN_MAX_AGE"])
        except (BadSignature, SignatureExpired):
            return None
        user = db.session.get(User, data.get("uid"))
        if user and user.password_hash[-16:] == data.get("h"):
            return user
        return None

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    slug = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))

    articles = db.relationship("Article", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), nullable=False, unique=True, index=True)
    # Taxonomie éditoriale — étiquette, ne change pas les champs disponibles
    # dans le formulaire (voir PLAN_REDACTION.md, §B) : une extension future,
    # pas construite tant que la simple étiquette n'a pas montré ses limites.
    article_type = db.Column(db.String(20), nullable=False, default="article")
    summary = db.Column(db.String(400), nullable=False)
    content = db.Column(db.Text, nullable=False)            # HTML assaini
    image_url = db.Column(db.String(400))
    image_credit = db.Column(db.String(200))
    is_premium = db.Column(db.Boolean, nullable=False, default=False)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    # 'brouillon', 'en_relecture', 'programme', 'publie' ou 'archive' — voir
    # _valider() dans blueprints/admin.py pour les règles de transition.
    status = db.Column(db.String(20), nullable=False, default="publie")
    # Renseigné uniquement quand status == "programme" : moment (UTC) où
    # `flask publish-scheduled` doit faire passer l'article en "publie".
    scheduled_at = db.Column(db.DateTime)
    source = db.Column(db.String(20), nullable=False, default="web")  # 'web', 'whatsapp', 'agregateur' ou 'reseaux_sociaux'
    # Renseignés uniquement quand source == "reseaux_sociaux" : l'URL du
    # post d'origine (Facebook pour l'instant) et la plateforme détectée.
    # Le post reste hébergé et rendu par la plateforme elle-même (widget
    # officiel embarqué dans templates/article.html) — jamais copié ni
    # réécrit ici. Voir README, section Réseaux sociaux, pour le détail.
    source_url = db.Column(db.String(500))
    source_platform = db.Column(db.String(20))
    views = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    category = db.relationship("Category", back_populates="articles")
    author = db.relationship("User", back_populates="articles")
    comments = db.relationship(
        "Comment", back_populates="article", cascade="all, delete-orphan",
        order_by="Comment.created_at.desc()",
    )

    @property
    def approved_comments(self):
        return [c for c in self.comments if c.status == "approuve"]

    def __repr__(self):
        return f"<Article {self.title!r}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="en_attente")
    reported = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"))

    article = db.relationship("Article", back_populates="comments")
    user = db.relationship("User", back_populates="comments")
    replies = db.relationship(
        "Comment", backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Comment {self.id} on article {self.article_id}>"


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    stripe_customer_id = db.Column(db.String(120))
    stripe_subscription_id = db.Column(db.String(120))
    status = db.Column(db.String(30), default="inactive")
    plan = db.Column(db.String(50), default="premium_mensuel")
    current_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="subscription")


class ModerationLog(db.Model):
    """Trace chaque action de modération — qui, quoi, quand.

    `actor_id` est vide pour une action automatique (filtre anti-spam, par
    exemple) : toute action n'est pas forcément humaine, mais toutes doivent
    rester traçables, y compris celles prises par le système lui-même.
    """
    __tablename__ = "moderation_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)   # 'commentaire' ou 'utilisateur'
    target_id = db.Column(db.Integer, nullable=False)
    detail = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    actor = db.relationship("User")

    def __repr__(self):
        return f"<ModerationLog {self.action} sur {self.target_type}#{self.target_id}>"


class Correspondent(db.Model):
    """Une personne autorisée à soumettre des articles par WhatsApp.

    Rattaché à un compte User "muet" (mot de passe aléatoire, jamais transmis)
    utilisé uniquement pour attribuer la signature des articles créés.
    """
    __tablename__ = "correspondents"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User")
    drafts = db.relationship(
        "WhatsAppDraft", backref="correspondent", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Correspondent {self.name} {self.phone_number}>"


class WhatsAppDraft(db.Model):
    """Brouillon en cours de composition par un correspondant.

    Accumule texte et image au fil des messages WhatsApp jusqu'à la commande
    PUBLIER, qui le convertit en Article (statut brouillon) et le supprime.
    """
    __tablename__ = "whatsapp_drafts"

    id = db.Column(db.Integer, primary_key=True)
    correspondent_id = db.Column(db.Integer, db.ForeignKey("correspondents.id"), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    text_buffer = db.Column(db.Text, default="")
    image_url = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ====================================================================
# Agrégation d'actualités (Mode 1 uniquement : titre + extrait + lien,
# jamais le contenu intégral — voir PLAN_AGREGATEUR.md).
# ====================================================================

COLLECTED_STATUSES = ("nouveau", "accepte", "rejete", "archive")


class Source(db.Model):
    """Un site externe surveillé via son flux RSS/Atom.

    Une source ne peut être activée (`is_active`) que si sa conformité a été
    vérifiée (`compliance_checked`) — appliqué au niveau de la route, pas
    seulement ici, mais rappelé par la contrainte ci-dessous pour qu'un accès
    direct à la base ne puisse pas non plus créer d'incohérence silencieuse.
    """
    __tablename__ = "sources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    site_url = db.Column(db.String(300), nullable=False)
    feed_url = db.Column(db.String(400), nullable=False)
    country = db.Column(db.String(80))

    # 0-100 : pondère le score de chaque article collecté depuis cette source.
    trust_level = db.Column(db.Integer, nullable=False, default=50)
    fetch_frequency_minutes = db.Column(db.Integer, nullable=False, default=60)

    # Termes séparés par des virgules — filtrage simple avant scoring.
    keywords_include = db.Column(db.String(500))
    keywords_exclude = db.Column(db.String(500))

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))

    compliance_checked = db.Column(db.Boolean, nullable=False, default=False)
    compliance_notes = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, nullable=False, default=False)

    # Classification de la source — seule une source gouvernementale ou
    # institutionnelle peut prétendre au mode intégral ci-dessous. Une
    # source "media" (valeur par défaut) reste en Mode 1 quoi qu'il arrive :
    # voir PLAN_AGREGATEUR.md, §0, sur la raison de cette distinction.
    source_category = db.Column(db.String(20), nullable=False, default="media")
    # "extrait" (Mode 1, par défaut) ou "integral" — l'intégral n'est
    # autorisé que pour une source gouvernementale/institutionnelle ET
    # accompagné d'une justification écrite, jamais l'un sans l'autre.
    content_mode = db.Column(db.String(20), nullable=False, default="extrait")
    # Trace écrite de la raison pour laquelle le mode intégral est justifié :
    # accord, conditions de syndication publiées, communiqué qui se déclare
    # lui-même libre de reproduction. Jamais une case cochée seule — voir
    # la conversation qui a motivé ce champ, conservée pour référence.
    content_license_justification = db.Column(db.Text)

    last_fetched_at = db.Column(db.DateTime)
    last_error = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship("Category")
    collected_articles = db.relationship(
        "CollectedArticle", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(
            "is_active = FALSE OR compliance_checked = TRUE",
            name="ck_source_active_requires_compliance",
        ),
        db.CheckConstraint(
            "content_mode = 'extrait' OR "
            "(source_category != 'media' AND content_license_justification IS NOT NULL "
            "AND length(content_license_justification) >= 20)",
            name="ck_source_integral_requires_justification",
        ),
    )

    def __repr__(self):
        return f"<Source {self.name}>"


class Topic(db.Model):
    """Regroupe plusieurs CollectedArticle qui semblent parler du même
    événement (titres proches, toutes sources confondues).
    """
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True)
    representative_title = db.Column(db.String(300), nullable=False)
    sources_count = db.Column(db.Integer, nullable=False, default=1)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow)

    articles = db.relationship("CollectedArticle", back_populates="topic")

    def __repr__(self):
        return f"<Topic {self.representative_title!r} ({self.sources_count} sources)>"


class CollectedArticle(db.Model):
    """Un item ramené par la collecte, avant toute décision éditoriale.

    Ne contient que titre, extrait et lien (Mode 1) — SAUF pour une source
    explicitement classée gouvernementale/institutionnelle et justifiée
    (Source.content_mode == "integral"), auquel cas `content_full` porte le
    texte intégral tel que fourni par le flux. Le stockage de ce champ suit
    toujours le mode de LA SOURCE au moment de la collecte, jamais une
    décision prise ailleurs.
    """
    __tablename__ = "collected_articles"

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=False)

    external_url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    excerpt = db.Column(db.Text)
    content_full = db.Column(db.Text)          # voir docstring : source gouv./institutionnelle uniquement
    image_url = db.Column(db.String(500))
    author = db.Column(db.String(200))
    language = db.Column(db.String(10), default="fr")

    published_at = db.Column(db.DateTime)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    status = db.Column(db.String(20), nullable=False, default="nouveau")

    score_total = db.Column(db.Float, default=0.0)
    score_importance = db.Column(db.Float, default=0.0)
    score_freshness = db.Column(db.Float, default=0.0)
    score_popularity = db.Column(db.Float, default=0.0)
    score_relevance = db.Column(db.Float, default=0.0)
    score_trust = db.Column(db.Float, default=0.0)

    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"))
    # Renseigné quand un admin accepte l'item : le brouillon Article créé.
    # SET NULL (pas CASCADE) si cet article est ensuite supprimé : l'item
    # collecté garde son historique de collecte, seul le lien se rompt.
    published_article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="SET NULL"))

    source = db.relationship("Source", back_populates="collected_articles")
    topic = db.relationship("Topic", back_populates="articles")
    published_article = db.relationship(
        "Article", backref=db.backref("collected_source", uselist=False)
    )

    __table_args__ = (
        db.UniqueConstraint("source_id", "external_url", name="uq_collected_source_url"),
    )

    @property
    def badge(self):
        """Classement visuel dérivé du score — voir ScoringConfig pour les seuils."""
        cfg = ScoringConfig.get_active()
        if self.score_total >= cfg.threshold_high:
            return "rouge"
        if self.score_total >= cfg.threshold_medium:
            return "orange"
        if self.score_total >= cfg.threshold_low:
            return "jaune"
        return "blanc"

    def __repr__(self):
        return f"<CollectedArticle {self.title!r}>"


class ScoringConfig(db.Model):
    """Pondérations du score, réglables depuis l'admin.

    Une seule ligne active à la fois (la plus récente) — on garde
    l'historique plutôt que d'écraser, au cas où il faudrait comprendre
    pourquoi un article a reçu tel score à telle date.
    """
    __tablename__ = "scoring_configs"

    id = db.Column(db.Integer, primary_key=True)

    weight_importance = db.Column(db.Float, nullable=False, default=0.30)
    weight_freshness = db.Column(db.Float, nullable=False, default=0.20)
    weight_popularity = db.Column(db.Float, nullable=False, default=0.20)
    weight_relevance = db.Column(db.Float, nullable=False, default=0.20)
    weight_trust = db.Column(db.Float, nullable=False, default=0.10)

    # Seuils de classement (0-100). Au-dessus de threshold_high : 🔴, etc.
    # En dessous de threshold_low : ⚪.
    threshold_high = db.Column(db.Float, nullable=False, default=75.0)
    threshold_medium = db.Column(db.Float, nullable=False, default=50.0)
    threshold_low = db.Column(db.Float, nullable=False, default=25.0)

    # Score de similarité (0-100, rapidfuzz token_set_ratio) au-delà duquel
    # deux titres sont considérés comme parlant du même événement. Calibré
    # empiriquement sur des titres réels : voir PLAN_AGREGATEUR.md, Phase 3,
    # pour la limite assumée de cette approche (les reformulations très
    # différentes du même événement ne sont pas rapprochées).
    topic_similarity_threshold = db.Column(db.Float, nullable=False, default=70.0)

    # Vocabulaire qui signale un événement potentiellement majeur, distinct
    # des mots-clés propres à chaque source (Source.keywords_include, qui
    # eux ciblent la pertinence thématique). Réglable depuis l'admin.
    importance_keywords = db.Column(db.Text, nullable=False, default=(
        "gouvernement, président, ministre, crise, mort, décès, accord, "
        "sommet, cedeao, onu, urgence, catastrophe, grève, élection, "
        "attentat, coup d'état, putsch, sécurité, armée"
    ))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_active():
        """Retourne la configuration la plus récente.

        Si aucune n'existe encore (site fraîchement installé), en persiste
        une avec les valeurs par défaut des colonnes ci-dessus. Un objet
        ScoringConfig() simplement construit sans être ajouté à la session
        n'aurait AUCUNE de ces valeurs par défaut — elles ne s'appliquent
        qu'à l'insertion réelle en base, pas à la construction Python. Sans
        ce commit, l'appelant recevrait des poids à None.
        """
        cfg = ScoringConfig.query.order_by(ScoringConfig.created_at.desc()).first()
        if cfg is None:
            cfg = ScoringConfig()
            db.session.add(cfg)
            db.session.commit()
        return cfg

    def __repr__(self):
        return f"<ScoringConfig #{self.id}>"


ARTICLE_TYPES = (
    "article", "breve", "depeche", "reportage", "interview", "analyse",
    "tribune", "chronique", "enquete", "portrait", "fact_checking",
)

TYPES_SOURCE_ARTICLE = ("site_officiel", "media", "reseau_social", "document", "interview")


class ArticleSource(db.Model):
    """Une source citée dans un article rédigé — distinct de
    CollectedArticle, qui trace l'origine d'un article venu de l'agrégateur.
    Ici, c'est le rédacteur qui déclare lui-même ses sources."""
    __tablename__ = "article_sources"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    nom = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    type_source = db.Column(db.String(30))
    citation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    article = db.relationship(
        "Article", backref=db.backref("sources_citees", cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<ArticleSource {self.nom!r}>"


class EditorialComment(db.Model):
    """Commentaire interne entre relecteur et auteur — jamais visible du
    lecteur public, à ne pas confondre avec le modèle Comment (lecteurs)."""
    __tablename__ = "editorial_comments"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    article = db.relationship(
        "Article", backref=db.backref("commentaires_editoriaux", cascade="all, delete-orphan")
    )
    author = db.relationship("User")

    def __repr__(self):
        return f"<EditorialComment sur article#{self.article_id}>"


class ArticleRevision(db.Model):
    """Historique champ par champ — qui a changé quoi, quand. Le champ
    "content" ne conserve pas le texte complet avant/après (volume), juste
    le fait qu'il a changé et de combien de caractères — voir
    blueprints/admin.py, _enregistrer_revisions()."""
    __tablename__ = "article_revisions"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    field_name = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    article = db.relationship(
        "Article", backref=db.backref("revisions", cascade="all, delete-orphan")
    )
    author = db.relationship("User")

    def __repr__(self):
        return f"<ArticleRevision {self.field_name} sur article#{self.article_id}>"


# =================================================================== PULAAR
# Module Pulaar, Phase 1 — voir PLAN_PULAAR.md. Modèle volontairement réduit
# par rapport au document d'origine (18 entités) : ce qui sert réellement un
# dictionnaire avec provenance et file de contribution modérée, pas plus.

PULAAR_TERM_STATUTS = ("documented", "validated")
PULAAR_PROPOSAL_STATUTS = ("en_attente", "valide", "rejete")


class PulaarDomain(db.Model):
    """Domaine thématique (Technologie, Quotidien, Agriculture...) — créé
    depuis l'admin, jamais une liste figée dans le code."""
    __tablename__ = "pulaar_domains"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True)

    def __repr__(self):
        return f"<PulaarDomain {self.name}>"


class PulaarSource(db.Model):
    """Provenance d'un terme — jamais une donnée sans source rattachée
    (voir PLAN_PULAAR.md, §A). method distingue une source externe
    (wiktionary, import_manuel) d'une contribution communautaire acceptée."""
    __tablename__ = "pulaar_sources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    license = db.Column(db.String(100))
    method = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return f"<PulaarSource {self.name}>"


class PulaarTerm(db.Model):
    """Un terme du dictionnaire. status distingue "documented" (vient d'une
    source ou d'une proposition acceptée, sans vérification linguistique
    supplémentaire) de "validated" (un admin/linguiste l'a explicitement
    confirmé) — jamais l'inverse, jamais présumé validé par défaut."""
    __tablename__ = "pulaar_terms"

    id = db.Column(db.Integer, primary_key=True)
    lemma = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), nullable=False, unique=True, index=True)
    part_of_speech = db.Column(db.String(50))
    status = db.Column(db.String(20), nullable=False, default="documented")
    domain_id = db.Column(db.Integer, db.ForeignKey("pulaar_domains.id", ondelete="SET NULL"))
    # Jamais nullable : un terme sans provenance ne devrait jamais exister.
    # Pas de ondelete ici, volontairement — supprimer une source qui a
    # encore des termes rattachés doit être bloqué, pas silencieusement
    # transformé en donnée orpheline.
    source_id = db.Column(db.Integer, db.ForeignKey("pulaar_sources.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    domain = db.relationship("PulaarDomain")
    source = db.relationship("PulaarSource")
    definitions = db.relationship(
        "PulaarDefinition", back_populates="term", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PulaarTerm {self.lemma!r}>"


class PulaarDefinition(db.Model):
    """Une définition d'un terme, dans une langue donnée (fr/en pour la
    Phase 1)."""
    __tablename__ = "pulaar_definitions"

    id = db.Column(db.Integer, primary_key=True)
    term_id = db.Column(db.Integer, db.ForeignKey("pulaar_terms.id", ondelete="CASCADE"), nullable=False)
    lang = db.Column(db.String(5), nullable=False)
    text = db.Column(db.Text, nullable=False)

    term = db.relationship("PulaarTerm", back_populates="definitions")

    def __repr__(self):
        return f"<PulaarDefinition {self.lang} sur terme#{self.term_id}>"


class PulaarProposal(db.Model):
    """Une suggestion communautaire, jamais publiée directement — même
    principe que CollectedArticle pour l'agrégateur média : une file de
    modération distincte du contenu final, jamais confondue avec lui."""
    __tablename__ = "pulaar_proposals"

    id = db.Column(db.Integer, primary_key=True)
    term_lemma = db.Column(db.String(200), nullable=False)
    definition_fr = db.Column(db.Text, nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey("pulaar_domains.id", ondelete="SET NULL"))
    justification = db.Column(db.Text)
    proposed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    status = db.Column(db.String(20), nullable=False, default="en_attente")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    domain = db.relationship("PulaarDomain")
    proposed_by = db.relationship("User")

    def __repr__(self):
        return f"<PulaarProposal {self.term_lemma!r} ({self.status})>"
