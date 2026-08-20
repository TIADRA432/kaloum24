"""Envoi d'e-mails via SMTP, sans dépendance supplémentaire.

Si aucun serveur SMTP n'est configuré, le message est écrit dans la console —
pratique en développement, et le site ne plante pas pour autant.
"""
import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to, subject, body):
    """Retourne True si l'e-mail est parti, False s'il a seulement été affiché."""
    server = current_app.config.get("MAIL_SERVER")

    if not server:
        current_app.logger.warning(
            "\n--- E-MAIL NON ENVOYÉ (SMTP non configuré) ---\n"
            "À       : %s\nObjet   : %s\n\n%s\n"
            "--- fin ---", to, subject, body,
        )
        return False

    message = EmailMessage()
    message["From"] = current_app.config["MAIL_SENDER"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(server, current_app.config["MAIL_PORT"], timeout=15) as smtp:
            if current_app.config["MAIL_USE_TLS"]:
                smtp.starttls()
            if current_app.config["MAIL_USERNAME"]:
                smtp.login(
                    current_app.config["MAIL_USERNAME"],
                    current_app.config["MAIL_PASSWORD"],
                )
            smtp.send_message(message)
        return True
    except Exception as exc:
        current_app.logger.error("Échec de l'envoi d'e-mail à %s : %s", to, exc)
        return False
