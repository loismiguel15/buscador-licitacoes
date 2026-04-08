from datetime import datetime
from functools import wraps
from flask import session, jsonify, redirect
from src.services.acesso_service import cliente_tem_acesso
from src.models import Usuario


def _sessao_valida():
    user_id = session.get("user_id")
    session_token = session.get("session_token")

    if not user_id or not session_token:
        return False

    usuario = Usuario.query.get(user_id)
    if not usuario or not usuario.ativo:
        return False

    if usuario.session_token != session_token:
        session.clear()
        return False

    if usuario.sessao_expira_em is not None and usuario.sessao_expira_em <= datetime.utcnow():
        session.clear()
        return False

    return True


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _sessao_valida():
            return jsonify({"error": "Não autenticado"}), 401
        return func(*args, **kwargs)
    return wrapper


def assinatura_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cliente_id = session.get("cliente_id")

        if not _sessao_valida() or not cliente_id:
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

        if not _sessao_valida() or not cliente_id:
            return redirect("/login.html")

        if not cliente_tem_acesso(cliente_id):
            return redirect("/pagamento/assinar")

        return func(*args, **kwargs)

    return wrapper
