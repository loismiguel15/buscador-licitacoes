from flask import Blueprint, jsonify, current_app, session, redirect
from src.models import db, Pagamento, Cliente
from src.services.efi_service import criar_link_pagamento
import os

pagamento_bp = Blueprint("pagamento", __name__, url_prefix="/pagamento")


@pagamento_bp.route("/criar/<int:cliente_id>", methods=["GET"])
def criar_pagamento(cliente_id):
    print("DATABASE URI:", current_app.config["SQLALCHEMY_DATABASE_URI"])
    print("PASTA ATUAL:", os.getcwd())

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

    resposta = criar_link_pagamento("Plano Monitoramento Licitações", 49.90)

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

    print("PAGAMENTO SALVO:", charge_id)

    return jsonify({
        "ok": True,
        "cliente_id": cliente_id,
        "charge_id": charge_id,
        "payment_url": payment_url,
        "status": status
    }), 201


@pagamento_bp.route("/assinar", methods=["GET"])
def assinar():
    print("DATABASE URI:", current_app.config["SQLALCHEMY_DATABASE_URI"])
    print("PASTA ATUAL:", os.getcwd())

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

    if pagamento_existente:
        return redirect(pagamento_existente.payment_url)

    resposta = criar_link_pagamento("Plano Monitoramento Licitações", 49.90)

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

    print("PAGAMENTO SALVO:", charge_id)

    return redirect(payment_url)