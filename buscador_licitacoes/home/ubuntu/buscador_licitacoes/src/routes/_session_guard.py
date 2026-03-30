from functools import wraps
from flask import session, jsonify, redirect
from src.services.acesso_service import cliente_tem_acesso


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Não autenticado"}), 401
        return func(*args, **kwargs)
    return wrapper


def assinatura_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cliente_id = session.get("cliente_id")

        if not cliente_id:
            return jsonify({"error": "Sessão inválida"}), 401

        if not cliente_tem_acesso(cliente_id):
            return jsonify({
                "error": "acesso_bloqueado",
                "message": "Seu período de teste expirou ou sua assinatura está inativa.",
                "redirect": "/pagamento/assinar"
            }), 403

        return func(*args, **kwargs)

    return wrapper


def assinatura_required_page(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cliente_id = session.get("cliente_id")

        if not cliente_id:
            return redirect("/login.html")

        if not cliente_tem_acesso(cliente_id):
            return redirect("/pagamento/assinar")

        return func(*args, **kwargs)

    return wrapper