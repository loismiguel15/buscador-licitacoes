from flask import Blueprint, jsonify, request, session
from src.models.user import User, db

user_bp = Blueprint("user", __name__)

LIMITE_USUARIOS = 3


@user_bp.route("/users", methods=["GET"])
def get_users():
    usuario_logado_id = session.get("user_id")
    cliente_id = session.get("cliente_id")
    tipo_usuario = session.get("tipo_usuario")

    if not usuario_logado_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    if tipo_usuario != "master":
        return jsonify({"erro": "Sem permissão para listar usuários"}), 403

    users = User.query.filter_by(cliente_id=cliente_id).all()
    return jsonify([user.to_dict() for user in users])


@user_bp.route("/users", methods=["POST"])
def create_user():
    usuario_logado_id = session.get("user_id")
    cliente_id = session.get("cliente_id")
    tipo_usuario = session.get("tipo_usuario")

    if not usuario_logado_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    if tipo_usuario != "master":
        return jsonify({"erro": "Apenas o usuário master pode criar novos usuários"}), 403

    data = request.get_json()

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    senha = data.get("senha", "").strip()

    if not username or not email or not senha:
        return jsonify({"erro": "Nome, email e senha são obrigatórios"}), 400

    usuario_existente = User.query.filter_by(email=email).first()
    if usuario_existente:
        return jsonify({"erro": "Já existe um usuário com esse email"}), 400

    total_ativos = User.query.filter_by(cliente_id=cliente_id, ativo=True).count()
    if total_ativos >= LIMITE_USUARIOS:
        return jsonify({
            "erro": f"Seu plano permite apenas {LIMITE_USUARIOS} usuários ativos"
        }), 400

    novo_usuario = User(
        cliente_id=cliente_id,
        username=username,
        email=email,
        tipo_usuario="comum",
        ativo=True,
        primeiro_acesso=True
    )
    novo_usuario.set_password(senha)

    db.session.add(novo_usuario)
    db.session.commit()

    return jsonify({
        "mensagem": "Usuário criado com sucesso",
        "usuario": novo_usuario.to_dict()
    }), 201


@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    usuario_logado_id = session.get("user_id")
    cliente_id = session.get("cliente_id")
    tipo_usuario = session.get("tipo_usuario")

    if not usuario_logado_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    if tipo_usuario != "master":
        return jsonify({"erro": "Sem permissão"}), 403

    user = User.query.filter_by(id=user_id, cliente_id=cliente_id).first()
    if not user:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    return jsonify(user.to_dict())


@user_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    usuario_logado_id = session.get("user_id")
    cliente_id = session.get("cliente_id")
    tipo_usuario = session.get("tipo_usuario")

    if not usuario_logado_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    if tipo_usuario != "master":
        return jsonify({"erro": "Sem permissão"}), 403

    user = User.query.filter_by(id=user_id, cliente_id=cliente_id).first()
    if not user:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    data = request.get_json()

    user.username = data.get("username", user.username).strip()
    novo_email = data.get("email", user.email).strip().lower()

    if novo_email != user.email:
        email_existente = User.query.filter_by(email=novo_email).first()
        if email_existente:
            return jsonify({"erro": "Já existe um usuário com esse email"}), 400
        user.email = novo_email

    if "ativo" in data:
        user.ativo = bool(data["ativo"])

    db.session.commit()
    return jsonify(user.to_dict())


@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    usuario_logado_id = session.get("user_id")
    cliente_id = session.get("cliente_id")
    tipo_usuario = session.get("tipo_usuario")

    if not usuario_logado_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    if tipo_usuario != "master":
        return jsonify({"erro": "Sem permissão"}), 403

    user = User.query.filter_by(id=user_id, cliente_id=cliente_id).first()
    if not user:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    if user.tipo_usuario == "master":
        return jsonify({"erro": "Não é permitido excluir o usuário master"}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({"mensagem": "Usuário removido com sucesso"}), 200