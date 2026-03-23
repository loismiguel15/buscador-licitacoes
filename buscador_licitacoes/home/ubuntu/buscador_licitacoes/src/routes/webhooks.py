from flask import Blueprint, jsonify

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.route("/api/webhooks/health", methods=["GET"])
def webhook_health():
    return jsonify({
        "ok": True,
        "message": "Webhook ativo"
    }), 200