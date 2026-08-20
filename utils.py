import html as html_module
import io
import os
import re
import unicodedata
import uuid
from datetime import datetime
from functools import wraps

import bleach
from flask import abort, current_app
from flask_login import current_user
from PIL import Image, ImageOps

# ---------------------------------------------------------------- rôles

def moderator_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_moderator:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------- texte

def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text) or "article"


def normaliser_texte(texte):
    """Minuscules et sans accents — partagé par le filtrage de mots-clés
    (collector.py), le regroupement par sujet (topic_matcher.py) et le
    scoring (scoring_engine.py) : un mot-clé tapé « guinee » doit retrouver
    un article écrit « Guinée » partout où cette comparaison a lieu."""
    sans_accents = unicodedata.normalize("NFKD", texte or "")
    sans_accents = sans_accents.encode("ascii", "ignore").decode("ascii")
    return sans_accents.lower()


def liste_mots_cles(chaine):
    """Découpe une chaîne 'mot1, mot2, mot3' en liste normalisée, sans vides."""
    return [normaliser_texte(m.strip()) for m in (chaine or "").split(",") if m.strip()]


def unique_slug(text, model, field="slug", exclude_id=None):
    """Génère un slug libre pour `model`, en suffixant -2, -3… si nécessaire."""
    base = slugify(text)
    candidate = base
    i = 2
    while True:
        query = model.query.filter(getattr(model, field) == candidate)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        if not query.first():
            return candidate
        candidate = f"{base}-{i}"
        i += 1


# Balises autorisées dans le contenu des articles (éditeur riche).
ALLOWED_TAGS = [
    "p", "br", "strong", "b", "em", "i", "u", "s", "blockquote",
    "h2", "h3", "h4", "ul", "ol", "li", "a", "img", "figure", "figcaption",
    "hr", "pre", "code", "span", "sub", "sup",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "span": ["class"],
    "p": ["class"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


# bleach retire la balise mais conserve son contenu textuel : pour <script> ou
# <style>, ce résidu n'est pas exécutable mais pollue l'article. On supprime
# donc ces blocs entièrement, contenu compris, avant de passer à bleach.
_BLOCS_DANGEREUX = re.compile(
    r"<\s*(script|style|iframe|object|embed|noscript)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_BALISES_ORPHELINES = re.compile(
    r"<\s*/?\s*(script|style|iframe|object|embed|noscript)\b[^>]*>",
    re.IGNORECASE,
)


def sanitize_html(raw_html):
    """Nettoie le HTML soumis par l'éditeur : supprime scripts, styles, handlers."""
    sans_blocs = _BLOCS_DANGEREUX.sub("", raw_html or "")
    sans_blocs = _BALISES_ORPHELINES.sub("", sans_blocs)

    cleaned = bleach.clean(
        sans_blocs,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    # Les liens externes s'ouvrent dans un nouvel onglet, sans fuite de referrer.
    return bleach.linkify(cleaned, callbacks=[_external_link])


def _external_link(attrs, new=False):
    href = attrs.get((None, "href"), "")
    if href.startswith("http"):
        attrs[(None, "target")] = "_blank"
        attrs[(None, "rel")] = "noopener noreferrer"
    return attrs


def strip_html(html):
    """Retourne le texte brut — utile pour les métadonnées et la lecture audio."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = bleach.clean(text, tags=[], strip=True)
    # Les flux RSS encodent souvent les apostrophes et guillemets en entités
    # numériques (&#8217; pour ’) : sans ce décodage, le texte affiché ou lu
    # à voix haute contiendrait le code brut au lieu du caractère. Sûr après
    # le nettoyage bleach ci-dessus : ce texte est ensuite ré-échappé par
    # Jinja à l'affichage, jamais inséré tel quel dans du HTML.
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def excerpt(html, length=160):
    text = strip_html(html)
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


def reading_time(html):
    """Temps de lecture estimé, en minutes (base 200 mots/minute)."""
    words = len(strip_html(html).split())
    return max(1, round(words / 200))


def text_to_paragraphs(text):
    """Convertit du texte brut (paragraphes séparés par une ligne vide) en HTML."""
    blocks = [b.strip() for b in (text or "").split("\n\n") if b.strip()]
    return "".join("<p>%s</p>" % bleach.clean(b, tags=[], strip=True) for b in blocks)


# ---------------------------------------------------------------- dates

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]
DAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def fr_date(dt, with_weekday=False):
    if dt is None:
        return ""
    parts = f"{dt.day} {MONTHS_FR[dt.month - 1]} {dt.year}"
    return f"{DAYS_FR[dt.weekday()]} {parts}" if with_weekday else parts


def fr_datetime(dt):
    if dt is None:
        return ""
    return f"{fr_date(dt)} à {dt.strftime('%H:%M')}"


def time_ago(dt):
    if dt is None:
        return ""
    seconds = int((datetime.utcnow() - dt).total_seconds())
    if seconds < 60:
        return "à l'instant"
    minutes = seconds // 60
    if minutes < 60:
        return f"il y a {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"il y a {hours} h"
    days = hours // 24
    if days < 7:
        return f"il y a {days} j"
    return fr_date(dt)


def rfc822(dt):
    """Format de date exigé par la spécification RSS 2.0."""
    if dt is None:
        return ""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return "%s, %02d %s %d %02d:%02d:%02d GMT" % (
        days[dt.weekday()], dt.day, months[dt.month - 1], dt.year,
        dt.hour, dt.minute, dt.second,
    )


# ---------------------------------------------------------------- images

def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    )


def _finalize_image(stream, ext):
    """Redimensionne, compresse et enregistre une image ouverte par PIL.

    Factorisé entre l'upload web (fichier) et l'upload WhatsApp (octets en
    mémoire) : les deux passent par le même traitement et les mêmes limites.
    """
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    name = f"{datetime.utcnow():%Y%m}-{uuid.uuid4().hex[:12]}.{ext}"
    path = os.path.join(upload_dir, name)

    try:
        image = Image.open(stream)
        image = ImageOps.exif_transpose(image)          # respecte l'orientation photo

        if ext == "gif":
            image.save(path, save_all=True)             # préserve l'animation
        else:
            max_width = current_app.config["IMAGE_MAX_WIDTH"]
            if image.width > max_width:
                ratio = max_width / float(image.width)
                image = image.resize(
                    (max_width, int(image.height * ratio)), Image.LANCZOS
                )
            if ext == "jpg" and image.mode in ("RGBA", "P", "LA"):
                image = image.convert("RGB")
            image.save(path, quality=current_app.config["IMAGE_QUALITY"], optimize=True)
    except Exception as exc:
        return None, f"Image illisible ou corrompue ({exc})."

    return f"/static/uploads/{name}", None


def save_uploaded_image(file_storage):
    """Enregistre une image envoyée depuis un formulaire web.

    Retourne (url, erreur). Une seule des deux valeurs est non nulle.
    """
    if not file_storage or not file_storage.filename:
        return None, "Aucun fichier reçu."

    if not allowed_image(file_storage.filename):
        autorisees = ", ".join(sorted(current_app.config["ALLOWED_IMAGE_EXTENSIONS"]))
        return None, f"Format non autorisé. Formats acceptés : {autorisees}."

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    if ext == "jpeg":
        ext = "jpg"
    return _finalize_image(file_storage.stream, ext)


def save_image_bytes(data, mime_type):
    """Enregistre une image reçue en mémoire (ex. pièce jointe WhatsApp).

    Retourne (url, erreur), comme save_uploaded_image.
    """
    ext_par_mime = {
        "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
        "image/webp": "webp", "image/gif": "gif",
    }
    ext = ext_par_mime.get((mime_type or "").split(";")[0].strip().lower())
    if not ext:
        return None, "Format d'image non reconnu."
    return _finalize_image(io.BytesIO(data), ext)


def normalize_phone(raw, country_code=None):
    """Normalise un numéro au format international attendu par WhatsApp
    (indicatif pays + numéro, chiffres seuls, sans '+').

    Un administrateur tape naturellement un numéro au format local
    (« 620 00 00 00 » ou « 0620000000 »), tandis que l'API WhatsApp envoie
    et attend le format international complet (« 224620000000 »). Sans cette
    conversion, un correspondant enregistré au format local ne serait jamais
    reconnu quand ses messages arrivent — l'échec serait silencieux et
    déroutant pour l'administrateur.

    `country_code` par défaut à WHATSAPP_COUNTRY_CODE (Guinée : 224). Un
    numéro qui commence déjà par cet indicatif est laissé tel quel.
    Retourne None si le résultat est trop court pour être un numéro valide.
    """
    if country_code is None:
        try:
            country_code = current_app.config["WHATSAPP_COUNTRY_CODE"]
        except RuntimeError:
            country_code = "224"          # hors contexte applicatif (ex. script)

    digits = re.sub(r"[^\d]", "", raw or "")
    if not digits:
        return None

    if not digits.startswith(country_code):
        digits = digits.lstrip("0")       # préfixe de tronc local (ex. le 0 de 0620...)
        digits = country_code + digits

    return digits if len(digits) >= 10 else None
