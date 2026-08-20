"""Client pour l'API WhatsApp Cloud (Meta) — envoi de messages, téléchargement
des médias reçus.

Isolé dans son propre module (plutôt que directement dans le blueprint) pour
que les tests puissent remplacer send_text et download_media par des
fonctions factices, sans appel réseau réel ni compte Meta.
"""
import json
import urllib.request

from flask import current_app


def _graph_base():
    return f"https://graph.facebook.com/{current_app.config['WHATSAPP_API_VERSION']}"


def send_text(to, body):
    """Envoie un message texte. Retourne True si l'envoi a réussi.

    Si aucun jeton n'est configuré (développement sans compte Meta), le
    message est simplement journalisé — le reste du flux continue de
    fonctionner normalement.
    """
    token = current_app.config["WHATSAPP_ACCESS_TOKEN"]
    phone_id = current_app.config["WHATSAPP_PHONE_NUMBER_ID"]

    if not token or not phone_id:
        current_app.logger.info(
            "[WhatsApp non configuré] message non envoyé à %s :\n%s", to, body
        )
        return False

    url = f"{_graph_base()}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        current_app.logger.error("Échec d'envoi WhatsApp à %s : %s", to, exc)
        return False


def download_media(media_id):
    """Télécharge une pièce jointe reçue (photo).

    L'API Meta se fait en deux temps : récupérer l'URL réelle du fichier,
    puis le télécharger — les deux appels nécessitent le jeton d'accès.
    Retourne (octets, type_mime) ou (None, None) en cas d'échec.
    """
    token = current_app.config["WHATSAPP_ACCESS_TOKEN"]
    if not token or not media_id:
        return None, None

    try:
        meta_req = urllib.request.Request(
            f"{_graph_base()}/{media_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(meta_req, timeout=10) as resp:
            meta = json.loads(resp.read().decode("utf-8"))

        media_url = meta["url"]
        mime_type = meta.get("mime_type", "image/jpeg")

        file_req = urllib.request.Request(
            media_url, headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(file_req, timeout=20) as resp:
            return resp.read(), mime_type
    except Exception as exc:
        current_app.logger.error("Échec de téléchargement du média %s : %s", media_id, exc)
        return None, None
