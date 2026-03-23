from flask import Blueprint, request, jsonify, session
from datetime import datetime
from src.models import db, Usuario, Assinatura, AssinaturaStatus
from src.routes._session_guard import login_required
from src.services.mercadopago_service import criar_preapproval

assinaturas_bp = Blueprint("assinaturas", __name__)

@assinaturas_bp.route("/api/assinaturas/checkout", methods=["POST"])
@login_required
def checkout_assinatura():
    data = request.get_json(force=True) or {}
    plano = (data.get("plano") or "PRO").upper()

    # precificação exemplo
    if plano == "PRO":
        valor = 29.90
    else:
        plano = "BASIC"
        valor = 19.90

    user_id = session["user_id"]
    cliente_id = session["cliente_id"]

    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({"error": "Usuário inválido"}), 401

    # cria assinatura no MP
    mp = criar_preapproval(payer_email=usuario.email, plano=plano, valor=valor)
    preapproval_id = mp.get("id")
    init_point = mp.get("init_point")

    # salva no banco como pending
    ass = Assinatura.query.filter_by(cliente_id=cliente_id).first()
    if not ass:
        ass = Assinatura(cliente_id=cliente_id)

    ass.status = AssinaturaStatus.PENDING
    ass.mp_preapproval_id = preapproval_id
    ass.mp_payer_email = usuario.email
    ass.updated_at = datetime.utcnow()

    db.session.add(ass)
    db.session.commit()

    return jsonify({
        "init_point": init_point,
        "mp_preapproval_id": preapproval_id,
        "plano": plano,
        "valor": valor
    }), 200