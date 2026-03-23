from flask import Blueprint, request, jsonify
from datetime import datetime
from src.models import db, Assinatura, AssinaturaStatus
from src.services.mercadopago_service import obter_preapproval

webhooks_bp = Blueprint("webhooks", __name__)

def mapear_status_mp(mp_status: str) -> AssinaturaStatus:
    s = (mp_status or "").lower()

    # comuns: authorized, cancelled, paused, pending
    if s in ("authorized", "active"):
        return AssinaturaStatus.ACTIVE
    if s in ("cancelled", "canceled"):
        return AssinaturaStatus.CANCELED
    if s in ("paused",):
        # se você não tiver PAUSED no enum, trate como INACTIVE ou PAST_DUE
        try:
            return AssinaturaStatus.PAST_DUE
        except Exception:
            return AssinaturaStatus.INACTIVE
    if s in ("pending",):
        return AssinaturaStatus.PENDING
    return AssinaturaStatus.PENDING

@webhooks_bp.route("/api/webhooks/mercadopago", methods=["POST"])
def mercadopago_webhook():
    payload = request.get_json(silent=True) or {}

    # formatos mais comuns: data.id ou id
    data = payload.get("data") or {}
    preapproval_id = data.get("id") or payload.get("id")

    if not preapproval_id:
        return jsonify({"ok": True, "ignored": True}), 200

    # busca status real na API do MP
    try:
        mp = obter_preapproval(preapproval_id)
    except Exception:
        # não derruba webhook
        return jsonify({"ok": True, "mp_fetch_failed": True}), 200

    mp_status = mp.get("status")  # authorized/cancelled/paused/pending

    ass = Assinatura.query.filter_by(mp_preapproval_id=preapproval_id).first()
    if not ass:
        return jsonify({"ok": True, "assinatura_not_found": True}), 200

    novo_status = mapear_status_mp(mp_status)

    ass.status = novo_status
    ass.updated_at = datetime.utcnow()

    # datas úteis
    if novo_status == AssinaturaStatus.ACTIVE and not ass.started_at:
        ass.started_at = datetime.utcnow()
    if novo_status == AssinaturaStatus.CANCELED:
        # se você quiser guardar cancelamento (adicione coluna canceled_at no model)
        if hasattr(ass, "canceled_at") and not ass.canceled_at:
            ass.canceled_at = datetime.utcnow()

    # se você adicionou mp_status/mp_last_event_at no model, preenche:
    if hasattr(ass, "mp_status"):
        ass.mp_status = mp_status
    if hasattr(ass, "mp_last_event_at"):
        ass.mp_last_event_at = datetime.utcnow()

    db.session.add(ass)
    db.session.commit()

    return jsonify({"ok": True}), 200