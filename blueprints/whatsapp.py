"""Publication d'articles par WhatsApp.

Un correspondant enregistré envoie du texte et éventuellement une photo ; le
tout s'accumule dans un brouillon (WhatsAppDraft) jusqu'à ce qu'il écrive
PUBLIER. À ce moment seulement, un Article est créé — toujours en statut
« brouillon » : rien n'est jamais publié automatiquement, un responsable de
la rédaction doit relire et publier depuis l'espace d'administration comme
n'importe quel autre article.

Un numéro qui n'est pas enregistré comme correspondant actif ne peut créer
aucun contenu ; il reçoit un message l'invitant à contacter la rédaction.
"""
import hashlib
import hmac

from flask import Blueprint, current_app, jsonify, request

import whatsapp_client
from extensions import db, limiter
from models import Article, Category, Correspondent, WhatsAppDraft
from utils import excerpt, normalize_phone, save_image_bytes, text_to_paragraphs, unique_slug

whatsapp_bp = Blueprint("whatsapp", __name__)

COMMANDES_PUBLIER = ("publier", "fin", "envoyer")
COMMANDES_ANNULER = ("annuler", "stop", "annulé")
COMMANDES_AIDE = ("aide", "help", "?")
COMMANDES_STATUT = ("statut", "état", "etat")

TEXTE_AIDE = (
    "Comment publier un article :\n"
    "1. Envoie ton texte (la première ligne devient le titre).\n"
    "2. Envoie une photo si tu en as une (facultatif).\n"
    "3. Écris PUBLIER pour transmettre à la rédaction.\n\n"
    "Autres commandes : ANNULER (effacer le brouillon), STATUT (voir "
    "l'avancement), AIDE (ce message).\n\n"
    "Ton article n'est jamais publié directement : un responsable de la "
    "rédaction le relit avant mise en ligne."
)


# ---------------------------------------------------------------- webhook

@whatsapp_bp.route("/webhook/whatsapp", methods=["GET"])
def verify():
    """Poignée de main exigée par Meta lors de la configuration du webhook."""
    if not current_app.config["WHATSAPP_ENABLED"]:
        return "Non trouvé.", 404

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge", "")

    attendu = current_app.config["WHATSAPP_VERIFY_TOKEN"]
    if mode == "subscribe" and attendu and token == attendu:
        return challenge, 200
    return "Jeton de vérification invalide.", 403


def _signature_valide(payload_bytes, signature_header, app_secret):
    """Vérifie que la requête provient bien de Meta (signature HMAC-SHA256).

    Sans secret configuré (développement local sans compte Meta), la
    vérification est ignorée — un avertissement est journalisé ailleurs, au
    démarrage, pour ne pas le répéter à chaque requête.
    """
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    attendu = hmac.new(app_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    recu = signature_header.split("sha256=", 1)[1]
    return hmac.compare_digest(attendu, recu)


@whatsapp_bp.route("/webhook/whatsapp", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_WEBHOOK"])
def incoming():
    if not current_app.config["WHATSAPP_ENABLED"]:
        return "Non trouvé.", 404

    payload = request.get_data()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not _signature_valide(payload, signature, current_app.config["WHATSAPP_APP_SECRET"]):
        return jsonify({"erreur": "signature invalide"}), 403

    data = request.get_json(silent=True) or {}

    # Meta exige un accusé de réception rapide ; toute erreur de traitement
    # est journalisée sans faire échouer la réponse, sous peine de retries
    # en boucle de la part de Meta.
    try:
        for entree in data.get("entry", []):
            for changement in entree.get("changes", []):
                for message in changement.get("value", {}).get("messages", []):
                    _traiter_message(message)
    except Exception:
        current_app.logger.exception("Erreur de traitement d'un message WhatsApp")

    return jsonify({"status": "ok"}), 200


# --------------------------------------------------------- traitement

def _traiter_message(message):
    numero = normalize_phone(message.get("from"))
    type_message = message.get("type")

    if not numero:
        return

    correspondant = Correspondent.query.filter_by(
        phone_number=numero, is_active=True
    ).first()

    if not correspondant:
        whatsapp_client.send_text(
            numero,
            f"Numéro non reconnu comme correspondant de {current_app.config['SITE_NAME']}. "
            "Contacte la rédaction pour être ajouté.",
        )
        return

    if type_message == "text":
        _traiter_texte(correspondant, message.get("text", {}).get("body", ""), numero)
    elif type_message == "image":
        _traiter_image(correspondant, message.get("image", {}), numero)
    else:
        whatsapp_client.send_text(
            numero,
            "Ce type de message n'est pas encore pris en charge. "
            "Envoie du texte ou une photo.",
        )


def _brouillon_de(correspondant):
    return WhatsAppDraft.query.filter_by(correspondent_id=correspondant.id).first()


def _traiter_texte(correspondant, texte, numero):
    texte = (texte or "").strip()
    if not texte:
        return
    commande = texte.lower()

    if commande in COMMANDES_PUBLIER:
        _finaliser(correspondant, numero)
        return

    if commande in COMMANDES_ANNULER:
        brouillon = _brouillon_de(correspondant)
        if brouillon:
            db.session.delete(brouillon)
            db.session.commit()
        whatsapp_client.send_text(numero, "Brouillon annulé.")
        return

    if commande in COMMANDES_AIDE:
        whatsapp_client.send_text(numero, TEXTE_AIDE)
        return

    if commande in COMMANDES_STATUT:
        _envoyer_statut(correspondant, numero)
        return

    brouillon = _brouillon_de(correspondant)
    if not brouillon:
        brouillon = WhatsAppDraft(
            correspondent_id=correspondant.id, phone_number=numero, text_buffer=texte
        )
        db.session.add(brouillon)
    else:
        brouillon.text_buffer = (
            (brouillon.text_buffer + "\n\n" + texte) if brouillon.text_buffer else texte
        )
    db.session.commit()

    whatsapp_client.send_text(
        numero, "Texte reçu. Envoie une photo si besoin, puis écris PUBLIER pour valider."
    )


def _traiter_image(correspondant, image_info, numero):
    media_id = image_info.get("id")
    legende = (image_info.get("caption") or "").strip()

    donnees, mime = whatsapp_client.download_media(media_id) if media_id else (None, None)
    if not donnees:
        whatsapp_client.send_text(numero, "Échec du téléchargement de la photo, réessaie.")
        return

    url, erreur = save_image_bytes(donnees, mime)
    if erreur:
        whatsapp_client.send_text(numero, "Photo invalide : " + erreur)
        return

    brouillon = _brouillon_de(correspondant)
    if not brouillon:
        brouillon = WhatsAppDraft(correspondent_id=correspondant.id, phone_number=numero)
        db.session.add(brouillon)

    brouillon.image_url = url
    if legende:
        brouillon.text_buffer = (
            (brouillon.text_buffer + "\n\n" + legende) if brouillon.text_buffer else legende
        )
    db.session.commit()

    whatsapp_client.send_text(numero, "Photo reçue. Écris PUBLIER pour valider ton article.")


def _envoyer_statut(correspondant, numero):
    brouillon = _brouillon_de(correspondant)
    if not brouillon or not (brouillon.text_buffer or brouillon.image_url):
        whatsapp_client.send_text(numero, "Aucun brouillon en cours. Envoie du texte pour commencer.")
        return

    longueur = len(brouillon.text_buffer or "")
    a_une_photo = "avec" if brouillon.image_url else "sans"
    whatsapp_client.send_text(
        numero,
        f"Brouillon en cours : {longueur} caractères de texte, {a_une_photo} photo. "
        "Écris PUBLIER pour valider ou ANNULER pour effacer.",
    )


def _finaliser(correspondant, numero):
    brouillon = _brouillon_de(correspondant)

    if not brouillon or not (brouillon.text_buffer and brouillon.text_buffer.strip()):
        whatsapp_client.send_text(
            numero, "Envoie d'abord un texte (titre + article) avant d'écrire PUBLIER."
        )
        return

    lignes = [l.strip() for l in brouillon.text_buffer.strip().split("\n") if l.strip()]
    titre = lignes[0][:200] if lignes else "Dépêche WhatsApp"
    corps_lignes = lignes[1:] if len(lignes) > 1 else lignes
    corps_html = text_to_paragraphs("\n\n".join(corps_lignes))
    resume = excerpt(corps_html, 200)
    if len(resume.strip()) < 10:
        resume = f"{titre} — dépêche envoyée par un correspondant via WhatsApp."[:400]

    categorie = (
        Category.query.filter_by(slug=current_app.config["WHATSAPP_DEFAULT_CATEGORY"]).first()
        or Category.query.order_by(Category.name).first()
    )
    if not categorie:
        whatsapp_client.send_text(
            numero, "Aucune rubrique n'est configurée sur le site. Préviens l'administrateur."
        )
        return

    article = Article(
        title=titre,
        slug=unique_slug(titre, Article),
        summary=resume,
        content=corps_html,
        image_url=brouillon.image_url,
        image_credit=(f"Photo : {correspondant.name} (WhatsApp)" if brouillon.image_url else None),
        category_id=categorie.id,
        author_id=correspondant.user_id,
        status="brouillon",
        source="whatsapp",
    )
    db.session.add(article)
    db.session.delete(brouillon)
    db.session.commit()

    prenom = correspondant.name.split()[0] if correspondant.name.split() else correspondant.name
    whatsapp_client.send_text(
        numero,
        f"Reçu ! « {titre} » est en file de relecture. Merci {prenom}.",
    )
