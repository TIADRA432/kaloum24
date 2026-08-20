from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Subscription

payments_bp = Blueprint("payments", __name__)


def _stripe_configured():
    return bool(current_app.config["STRIPE_SECRET_KEY"] and current_app.config["STRIPE_PRICE_ID"])


@payments_bp.route("/abonnement")
def subscribe():
    return render_template("subscribe.html", stripe_ready=_stripe_configured())


@payments_bp.route("/abonnement/checkout", methods=["POST"])
@login_required
def create_checkout_session():
    if not _stripe_configured():
        flash(
            "Les paiements Stripe ne sont pas encore configurés sur ce site "
            "(clés manquantes côté serveur). Voir le README.",
            "error",
        )
        return redirect(url_for("payments.subscribe"))

    if current_user.is_subscriber:
        flash("Tu es déjà abonné.", "info")
        return redirect(url_for("main.home"))

    import stripe

    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=current_user.email,
            line_items=[{"price": current_app.config["STRIPE_PRICE_ID"], "quantity": 1}],
            success_url=url_for("payments.success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("payments.subscribe", _external=True),
            client_reference_id=str(current_user.id),
        )
    except Exception as exc:  # pragma: no cover - dépend d'un service externe
        flash(f"Erreur Stripe : {exc}", "error")
        return redirect(url_for("payments.subscribe"))

    return redirect(checkout_session.url, code=303)


@payments_bp.route("/abonnement/succes")
@login_required
def success():
    flash("Paiement reçu — l'activation de ton abonnement peut prendre quelques instants.", "success")
    return redirect(url_for("main.home"))


@payments_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    """Reçoit les événements Stripe (activation/annulation d'abonnement).

    À configurer dans le dashboard Stripe avec l'URL publique de cette route
    et à pointer vers STRIPE_WEBHOOK_SECRET. Voir le README.
    """
    if not current_app.config["STRIPE_WEBHOOK_SECRET"]:
        return jsonify({"error": "webhook non configuré"}), 400

    import stripe

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config["STRIPE_WEBHOOK_SECRET"]
        )
    except (ValueError, Exception) as exc:  # signature invalide ou payload malformé
        return jsonify({"error": str(exc)}), 400

    event_type = event["type"]
    data = event["data"]["object"]

    from models import User

    if event_type == "checkout.session.completed":
        user_id = data.get("client_reference_id")
        user = User.query.get(int(user_id)) if user_id else None
        if user:
            user.is_subscriber = True
            user.stripe_customer_id = data.get("customer")
            sub = user.subscription or Subscription(user_id=user.id)
            sub.stripe_customer_id = data.get("customer")
            sub.stripe_subscription_id = data.get("subscription")
            sub.status = "active"
            db.session.add(sub)
            db.session.commit()

    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        customer_id = data.get("customer")
        sub = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
        if sub:
            status = data.get("status")
            sub.status = status
            if status not in ("active", "trialing"):
                sub.user.is_subscriber = False
            else:
                sub.user.is_subscriber = True
            db.session.commit()

    return jsonify({"received": True})
