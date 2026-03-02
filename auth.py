from flask import Blueprint, request, jsonify, session
from src.models import db, Cliente, Usuario, TipoUsuario
from werkzeug.security import generate_password_hash, check_password_hash
import re

auth_bp = Blueprint("auth", __name__)

# Basic validation functions (can be expanded)
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_cnpj(cnpj):
    # Basic format check, not a full validation
    return re.match(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", cnpj)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    # --- Client Data --- 
    nome_empresa = data.get("nome_empresa")
    cnpj = data.get("cnpj")
    email_contato = data.get("email_contato")
    telefone_contato = data.get("telefone_contato")

    # --- Master User Data ---
    nome_master = data.get("nome_master")
    email_master = data.get("email_master")
    senha_master = data.get("senha_master")
    confirma_senha_master = data.get("confirma_senha_master")

    # --- Basic Validation --- 
    if not all([nome_empresa, cnpj, email_contato, nome_master, email_master, senha_master, confirma_senha_master]):
        return jsonify({"error": "Todos os campos obrigatórios devem ser preenchidos."}), 400

    if not is_valid_cnpj(cnpj):
        return jsonify({"error": "Formato de CNPJ inválido."}), 400

    if not is_valid_email(email_contato) or not is_valid_email(email_master):
        return jsonify({"error": "Formato de email inválido."}), 400

    if senha_master != confirma_senha_master:
        return jsonify({"error": "As senhas do usuário master não coincidem."}), 400
    
    if len(senha_master) < 6: # Example minimum length
         return jsonify({"error": "A senha deve ter pelo menos 6 caracteres."}), 400

    # --- Check for existing data --- 
    if Cliente.query.filter_by(cnpj=cnpj).first():
        return jsonify({"error": "CNPJ já cadastrado."}), 409 # 409 Conflict

    if Usuario.query.filter_by(email=email_master).first():
        return jsonify({"error": "Email do usuário master já cadastrado."}), 409

    # --- Create records --- 
    try:
        novo_cliente = Cliente(
            nome_empresa=nome_empresa,
            cnpj=cnpj,
            email_contato=email_contato,
            telefone_contato=telefone_contato
        )
        db.session.add(novo_cliente)
        # Flush to get the new client ID before creating the user
        db.session.flush()

        novo_usuario_master = Usuario(
            cliente_id=novo_cliente.id,
            nome_completo=nome_master,
            email=email_master,
            tipo=TipoUsuario.MASTER # Set type to MASTER
        )
        novo_usuario_master.set_password(senha_master) # Hash the password
        db.session.add(novo_usuario_master)

        db.session.commit()
        return jsonify({"message": "Conta criada com sucesso!"}), 201

    except Exception as e:
        db.session.rollback()
        # Log the error e
        print(f"Error during registration: {e}") # Basic logging
        return jsonify({"error": "Erro ao criar conta. Tente novamente mais tarde."}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")

    if not email or not senha:
        return jsonify({"error": "Email e senha são obrigatórios."}), 400

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario or not usuario.check_password(senha) or not usuario.ativo:
        return jsonify({"error": "Credenciais inválidas ou usuário inativo."}), 401 # Unauthorized
    
    # Update last login time
    try:
        usuario.ultimo_login = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error updating last login: {e}") # Basic logging
        # Non-critical error, proceed with login

    # Store user info in session (simple session management)
    session["user_id"] = usuario.id
    session["user_email"] = usuario.email
    session["user_tipo"] = usuario.tipo.value # Store enum value
    session["cliente_id"] = usuario.cliente_id

    return jsonify({
        "message": "Login bem-sucedido!",
        "user": {
            "id": usuario.id,
            "email": usuario.email,
            "nome": usuario.nome_completo,
            "tipo": usuario.tipo.value
        }
    }), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    # Clear session data
    session.pop("user_id", None)
    session.pop("user_email", None)
    session.pop("user_tipo", None)
    session.pop("cliente_id", None)
    return jsonify({"message": "Logout bem-sucedido!"}), 200

@auth_bp.route("/status", methods=["GET"])
def status():
    if "user_id" in session:
        return jsonify({
            "logged_in": True,
            "user": {
                "id": session["user_id"],
                "email": session["user_email"],
                "tipo": session["user_tipo"],
                "cliente_id": session["cliente_id"]
            }
        }), 200
    else:
        return jsonify({"logged_in": False}), 200

