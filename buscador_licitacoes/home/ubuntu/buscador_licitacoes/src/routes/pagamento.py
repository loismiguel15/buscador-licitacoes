from flask import Blueprint, jsonify, current_app, session, redirect
from src.models import db, Pagamento, Cliente, Usuario
from src.services.efi_service import criar_link_pagamento
from src.routes._session_guard import login_required

pagamento_bp = Blueprint("pagamento", __name__, url_prefix="/pagamento")


@pagamento_bp.route("/criar/<int:cliente_id>", methods=["GET"])
@login_required
def criar_pagamento(cliente_id):
    try:
        cliente_id_sessao = session.get("cliente_id")
        if not cliente_id_sessao or cliente_id_sessao != cliente_id:
            return jsonify({
                "ok": False,
                "erro": "Acesso negado"
            }), 403

        cliente = Cliente.query.get(cliente_id)

        if not cliente:
            return jsonify({
                "ok": False,
                "erro": "Cliente não encontrado"
            }), 404

        pagamento_existente = Pagamento.query.filter_by(
            cliente_id=cliente_id,
            status="link"
        ).first()

        if pagamento_existente:
            return jsonify({
                "ok": True,
                "msg": "Cobrança já existente",
                "cliente_id": cliente_id,
                "charge_id": pagamento_existente.charge_id,
                "payment_url": pagamento_existente.payment_url,
                "status": pagamento_existente.status
            }), 200

        email_cliente = cliente.email_contato or "teste@teste.com"

        resposta = criar_link_pagamento(
            "Plano Monitoramento Licitações",
            49.90,
            email_cliente
        )

        charge_id = str(resposta["data"]["charge_id"])
        payment_url = resposta["data"]["payment_url"]
        status = resposta["data"]["status"]
        valor = 49.90

        pagamento = Pagamento(
            cliente_id=cliente_id,
            charge_id=charge_id,
            payment_url=payment_url,
            status=status,
            valor=valor,
        )

        db.session.add(pagamento)
        db.session.commit()

        current_app.logger.info("Pagamento criado para cliente_id=%s charge_id=%s", cliente_id, charge_id)

        return jsonify({
            "ok": True,
            "cliente_id": cliente_id,
            "charge_id": charge_id,
            "payment_url": payment_url,
            "status": status
        }), 201

    except Exception:
        current_app.logger.exception("Erro ao criar pagamento para cliente_id=%s", cliente_id)
        return jsonify({
            "ok": False,
            "erro": "Erro ao criar pagamento."
        }), 500


@pagamento_bp.route("/assinar", methods=["GET"])
@login_required
def assinar():
    try:
        cliente_id = session.get("cliente_id")

        if not cliente_id:
            return redirect("/login.html")

        cliente = Cliente.query.get(cliente_id)

        if not cliente:
            return jsonify({
                "ok": False,
                "erro": "Cliente não encontrado"
            }), 404

        pagamento_existente = Pagamento.query.filter_by(
            cliente_id=cliente_id,
            status="link"
        ).first()

        if pagamento_existente and pagamento_existente.payment_url:
            return redirect(pagamento_existente.payment_url)

        email_cliente = cliente.email_contato or "teste@teste.com"

        resposta = criar_link_pagamento(
            "Plano Monitoramento Licitações",
            49.90,
            email_cliente
        )

        charge_id = str(resposta["data"]["charge_id"])
        payment_url = resposta["data"]["payment_url"]
        status = resposta["data"]["status"]
        valor = 49.90

        pagamento = Pagamento(
            cliente_id=cliente_id,
            charge_id=charge_id,
            payment_url=payment_url,
            status=status,
            valor=valor,
        )

        db.session.add(pagamento)
        db.session.commit()

        current_app.logger.info("Pagamento criado via /assinar para cliente_id=%s charge_id=%s", cliente_id, charge_id)

        return redirect(payment_url)

    except Exception:
        current_app.logger.exception("Erro na rota /pagamento/assinar")
        return jsonify({
            "ok": False,
            "erro": "Erro ao iniciar assinatura."
        }), 500
