from flask import Blueprint, request, jsonify, session
from datetime import datetime
from src.models import db, Usuario, Assinatura, AssinaturaStatus
from src.routes._session_guard import login_required

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

    user_id = session.get("user_id")
    cliente_id = session.get("cliente_id")

    if not user_id or not cliente_id:
        return jsonify({"error": "Sessão inválida"}), 401

    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({"error": "Usuário inválido"}), 401

    # procura assinatura existente
    ass = Assinatura.query.filter_by(cliente_id=cliente_id).first()
    if not ass:
        ass = Assinatura(cliente_id=cliente_id)

    # marca como pendente até integrar com EFI
    ass.status = AssinaturaStatus.PENDING
    ass.updated_at = datetime.utcnow()

    # preenche campos se existirem no model
    if hasattr(ass, "plano"):
        ass.plano = plano
    if hasattr(ass, "valor"):
        ass.valor = valor
    if hasattr(ass, "email_pagador"):
        ass.email_pagador = usuario.email

    db.session.add(ass)
    db.session.commit()

    return jsonify({
        "ok": True,
        "message": "Checkout iniciado com sucesso",
        "plano": plano,
        "valor": valor,
        "status": "pending"
    }), 200