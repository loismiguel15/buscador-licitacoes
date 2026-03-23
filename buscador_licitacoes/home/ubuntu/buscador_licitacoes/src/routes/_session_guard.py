from functools import wraps
from flask import session, jsonify

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Não autenticado"}), 401
        return fn(*args, **kwargs)
    return wrapper

def master_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Não autenticado"}), 401
        if session.get("user_tipo") != "master":
            return jsonify({"error": "Acesso permitido apenas para usuário master"}), 403
        return fn(*args, **kwargs)
    return wrapper