from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime, timedelta
import re
import random
import secrets
from datetime import datetime, timedelta
from src.models import db, Cliente, Usuario, TipoUsuario, Assinatura, AssinaturaStatus
from src.services.cnpj_serpro_service import consultar_cnpj_basica
from src.services.email_service import enviar_codigo_recuperacao_senha
from datetime import timezone
from flask import jsonify

auth_bp = Blueprint("auth", __name__)
LIMITE_USUARIOS_ATIVOS = 3
CNPJ_LOOKUP_TTL_MINUTOS = 15
RATE_LIMIT_STORAGE = {}
RATE_LIMIT_RULES = {
    "cnpj_lookup": {"max_attempts": 20, "window_seconds": 300},
    "register": {"max_attempts": 10, "window_seconds": 3600},
    "login": {"max_attempts": 10, "window_seconds": 900},
    "forgot_password": {"max_attempts": 5, "window_seconds": 900},
    "verify_reset_code": {"max_attempts": 8, "window_seconds": 900},
    "reset_password": {"max_attempts": 5, "window_seconds": 900},
}

# -------------------------
# Helpers
# -------------------------

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", (email or "").strip()))


def only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def is_valid_cnpj_format(cnpj: str) -> bool:
    return len(only_digits(cnpj)) == 14


def is_valid_cnpj_dv(cnpj: str) -> bool:
    cnpj = only_digits(cnpj)
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False

    def calc_dv(base: str, weights):
        s = sum(int(d) * w for d, w in zip(base, weights))
        r = s % 11
        return "0" if r < 2 else str(11 - r)

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    dv1 = calc_dv(cnpj[:12], w1)
    dv2 = calc_dv(cnpj[:12] + dv1, w2)
    return cnpj[-2:] == (dv1 + dv2)


def normalize_situacao(data: dict) -> str:
    situ = (data.get("descricao_situacao_cadastral") or data.get("situacao") or "")
    return str(situ).strip().upper()


def extract_nome_empresa(data: dict) -> str:
    return (
        data.get("razao_social")
        or data.get("nome_empresarial")
        or data.get("nome")
        or ""
    ).strip()


def sanitize_phone(phone: str) -> str:
    return only_digits(phone or "")


def is_valid_phone(phone_digits: str) -> bool:
    if not phone_digits:
        return True
    return len(phone_digits) in (10, 11)


def get_usuario_logado():

    user_id = session.get("user_id")
    session_token = session.get("session_token")

    if not user_id or not session_token:
        return None

    usuario = Usuario.query.get(user_id)

    if not usuario:
        return None

    if not usuario.ativo:
        return None

    # 🔐 verifica se sessão é válida
    if usuario.session_token != session_token:
        session.clear()
        return None

    # 🔐 verifica expiração
    if usuario.sessao_expira_em and usuario.sessao_expira_em < datetime.utcnow():
        session.clear()
        return None

    return usuario


def require_master():
    usuario_logado = get_usuario_logado()
    if not usuario_logado:
        return None, (jsonify({"error": "Não autenticado."}), 401)

    if usuario_logado.tipo != TipoUsuario.MASTER:
        return None, (
            jsonify({
                "error": "Acesso negado. Apenas usuário master pode realizar esta ação."
            }),
            403
        )

    return usuario_logado, None


def is_strong_password(password: str) -> bool:
    if not password or len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[^A-Za-z\d]", password):
        return False
    return True


def gerar_codigo_reset() -> str:
    return f"{random.randint(0, 999999):06d}"


def _get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _cleanup_rate_limit_bucket(now):
    expirados = [
        chave for chave, bucket in RATE_LIMIT_STORAGE.items()
        if bucket["reset_at"] <= now
    ]
    for chave in expirados:
        RATE_LIMIT_STORAGE.pop(chave, None)


def check_rate_limit(action: str, identifier: str):
    rule = RATE_LIMIT_RULES[action]
    now = datetime.utcnow()
    _cleanup_rate_limit_bucket(now)

    bucket_key = f"{action}:{identifier}"
    bucket = RATE_LIMIT_STORAGE.get(bucket_key)

    if not bucket or bucket["reset_at"] <= now:
        bucket = {
            "count": 0,
            "reset_at": now + timedelta(seconds=rule["window_seconds"])
        }
        RATE_LIMIT_STORAGE[bucket_key] = bucket

    bucket["count"] += 1
    if bucket["count"] > rule["max_attempts"]:
        retry_after = max(1, int((bucket["reset_at"] - now).total_seconds()))
        return retry_after

    return None


def throttle_or_response(action: str, identifier: str):
    retry_after = check_rate_limit(action, identifier)
    if retry_after is None:
        return None

    response = jsonify({
        "error": "Muitas tentativas. Tente novamente em instantes."
    })
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def reset_rate_limit(action: str, identifier: str):
    RATE_LIMIT_STORAGE.pop(f"{action}:{identifier}", None)


# -------------------------
# Lookup do CNPJ
# -------------------------

@auth_bp.route("/cnpj/lookup", methods=["GET"])
def cnpj_lookup():
    throttled = throttle_or_response("cnpj_lookup", _get_client_ip())
    if throttled:
        return throttled

    cnpj = request.args.get("cnpj", "")
    cnpj_digits = only_digits(cnpj)

    if len(cnpj_digits) != 14:
        return jsonify({"ok": False, "error": "CNPJ deve ter 14 dígitos."}), 200

    if not is_valid_cnpj_dv(cnpj_digits):
        return jsonify({"ok": False, "error": "CNPJ inválido (DV não confere)."}), 200

    try:
        cnpj_info = consultar_cnpj_basica(cnpj_digits)
    except Exception:
        current_app.logger.exception("Erro no lookup de CNPJ")
        return jsonify({"ok": False, "error": "Falha ao consultar CNPJ."}), 502

    if not cnpj_info.get("ok"):
        return jsonify({
            "ok": False,
            "error": cnpj_info.get("error", "CNPJ não encontrado.")
        }), 200

    data = cnpj_info.get("data") or {}

    nome = extract_nome_empresa(data)
    situacao = normalize_situacao(data)
    municipio = (data.get("municipio") or "").strip()
    uf = (data.get("uf") or "").strip().upper()
    nome_fantasia = (data.get("nome_fantasia") or "").strip()

    session["cnpj_lookup_validado"] = {
        "cnpj": cnpj_digits,
        "nome_empresa": nome,
        "nome_fantasia": nome_fantasia,
        "situacao": situacao,
        "municipio": municipio,
        "uf": uf,
        "data": data,
        "validated_at": datetime.utcnow().isoformat()
    }

    return jsonify({
        "ok": True,
        "cnpj": cnpj_digits,
        "nome_empresa": nome,
        "nome_fantasia": nome_fantasia,
        "situacao": situacao,
        "municipio": municipio,
        "uf": uf
    }), 200


# -------------------------
# Register
# -------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    client_ip = _get_client_ip()
    throttled = throttle_or_response("register", client_ip)
    if throttled:
        return throttled

    data = request.get_json(silent=True) or {}

    nome_empresa = (data.get("nome_empresa") or "").strip()
    cnpj = (data.get("cnpj") or "").strip()
    email_contato = (data.get("email_contato") or "").strip()
    telefone_contato_raw = (data.get("telefone_contato") or "").strip()

    nome_master = (data.get("nome_master") or "").strip()
    email_master = (data.get("email_master") or "").strip()
    senha_master = data.get("senha_master") or ""
    confirma_senha_master = data.get("confirma_senha_master") or ""

    if not all([nome_empresa, cnpj, email_contato, nome_master, email_master, senha_master, confirma_senha_master]):
        return jsonify({"error": "Todos os campos obrigatórios devem ser preenchidos."}), 400

    if not is_valid_email(email_contato) or not is_valid_email(email_master):
        return jsonify({"error": "Formato de email inválido."}), 400

    if senha_master != confirma_senha_master:
        return jsonify({"error": "As senhas do usuário master não coincidem."}), 400

    if not is_strong_password(senha_master):
        return jsonify({
            "error": "A senha deve ter no mínimo 8 caracteres, incluindo letra maiúscula, letra minúscula, número e caractere especial."
        }), 400

    if not is_valid_cnpj_format(cnpj):
        return jsonify({"error": "CNPJ inválido (precisa ter 14 dígitos)."}), 400

    cnpj_digits = only_digits(cnpj)
    if not is_valid_cnpj_dv(cnpj_digits):
        return jsonify({"error": "CNPJ inválido (dígitos verificadores não conferem)."}), 400

    telefone_digits = sanitize_phone(telefone_contato_raw)
    if not is_valid_phone(telefone_digits):
        return jsonify({"error": "Telefone inválido. Use DDD + número (10 ou 11 dígitos)."}), 400

    if Cliente.query.filter_by(cnpj=cnpj_digits).first():
        return jsonify({"error": "CNPJ já cadastrado."}), 409

    if Usuario.query.filter_by(email=email_master).first():
        return jsonify({"error": "Email do usuário master já cadastrado."}), 409

    lookup_cache = session.get("cnpj_lookup_validado")

    if not lookup_cache or lookup_cache.get("cnpj") != cnpj_digits:
        return jsonify({
            "error": "Validação do CNPJ expirou ou não foi encontrada. Consulte o CNPJ novamente antes de criar a conta."
        }), 400

    validated_at_raw = lookup_cache.get("validated_at")
    try:
        validated_at = datetime.fromisoformat(validated_at_raw) if validated_at_raw else None
    except ValueError:
        validated_at = None

    if not validated_at or validated_at < datetime.utcnow() - timedelta(minutes=CNPJ_LOOKUP_TTL_MINUTOS):
        session.pop("cnpj_lookup_validado", None)
        return jsonify({
            "error": "Validação do CNPJ expirou. Consulte o CNPJ novamente antes de criar a conta."
        }), 400

    situacao = (lookup_cache.get("situacao") or "").strip().upper()
    if situacao != "ATIVA":
        return jsonify({
            "error": f"CNPJ não está ATIVO. Situação atual: {situacao or 'DESCONHECIDA'}"
        }), 400

    nome_api = (lookup_cache.get("nome_empresa") or "").strip()
    if nome_api:
        nome_empresa = nome_api

    try:
        novo_token = secrets.token_hex(32)

        novo_cliente = Cliente(
            nome_empresa=nome_empresa,
            cnpj=cnpj_digits,
            email_contato=email_contato,
            telefone_contato=telefone_digits or None
        )
        db.session.add(novo_cliente)
        db.session.flush()

        nova_assinatura = Assinatura(
            cliente_id=novo_cliente.id,
            status=AssinaturaStatus.PENDING,
            provider="efi",
            provider_ref=None,
            provider_status="trial",
            started_at=datetime.utcnow(),
            trial_ends_at=datetime.utcnow() + timedelta(days=10)
        )
        db.session.add(nova_assinatura)

        novo_usuario_master = Usuario(
            cliente_id=novo_cliente.id,
            nome_completo=nome_master,
            email=email_master,
            tipo=TipoUsuario.MASTER,
            ativo=True
        )
        novo_usuario_master.set_password(senha_master)
        novo_usuario_master.ultimo_login = datetime.utcnow()
        novo_usuario_master.session_token = novo_token
        novo_usuario_master.ultimo_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        novo_usuario_master.ultimo_user_agent = request.headers.get("User-Agent")
        novo_usuario_master.sessao_expira_em = datetime.utcnow() + timedelta(hours=12)

        db.session.add(novo_usuario_master)
        db.session.commit()

        session["user_id"] = novo_usuario_master.id
        session["session_token"] = novo_usuario_master.session_token
        session["user_email"] = novo_usuario_master.email
        session["user_tipo"] = novo_usuario_master.tipo.value
        session["cliente_id"] = novo_usuario_master.cliente_id
        session.permanent = True

        session.pop("cnpj_lookup_validado", None)
        reset_rate_limit("register", client_ip)

        return jsonify({
            "message": "Conta criada com sucesso! Você já está logado.",
            "trial": {
                "status": "ativo",
                "dias_gratis": 10,
                "trial_ends_at": nova_assinatura.trial_ends_at.isoformat()
            },
            "user": {
                "id": novo_usuario_master.id,
                "email": novo_usuario_master.email,
                "nome": novo_usuario_master.nome_completo,
                "tipo": novo_usuario_master.tipo.value
            }
        }), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao criar conta (register)")
        return jsonify({"error": "Erro ao criar conta. Tente novamente mais tarde."}), 500


# -------------------------
# Login
# -------------------------

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    senha = data.get("senha") or ""
    rate_limit_key = f"{_get_client_ip()}:{email or 'sem-email'}"

    throttled = throttle_or_response("login", rate_limit_key)
    if throttled:
        return throttled

    if not email or not senha:
        return jsonify({"error": "Email e senha são obrigatórios."}), 400

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario or not usuario.check_password(senha) or not usuario.ativo:
        return jsonify({"error": "Credenciais inválidas ou usuário inativo."}), 401

    # trata tipo como Enum ou string
    tipo_usuario = usuario.tipo.value if hasattr(usuario.tipo, "value") else str(usuario.tipo).lower()

    try:
        import secrets
        from datetime import datetime, timedelta

        novo_token = secrets.token_hex(32)

        usuario.session_token = novo_token
        usuario.ultimo_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        usuario.ultimo_user_agent = request.headers.get("User-Agent")
        usuario.sessao_expira_em = datetime.utcnow() + timedelta(hours=12)
        usuario.ultimo_login = datetime.utcnow()

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Erro atualizando sessão de login")
        return jsonify({"error": "Erro ao realizar login. Tente novamente."}), 500

    session["user_id"] = usuario.id
    session["session_token"] = usuario.session_token
    session["user_email"] = usuario.email
    session["user_tipo"] = tipo_usuario
    session["cliente_id"] = usuario.cliente_id
    session.permanent = True
    reset_rate_limit("login", rate_limit_key)

    # somente usuário comum precisa trocar senha no primeiro acesso
    precisa_trocar_senha = (
        tipo_usuario == "comum" and bool(getattr(usuario, "primeiro_acesso", False))
    )

    return jsonify({
        "message": "Login bem-sucedido!",
        "user": {
            "id": usuario.id,
            "email": usuario.email,
            "nome": usuario.nome_completo,
            "tipo": tipo_usuario,
            "primeiro_acesso": bool(getattr(usuario, "primeiro_acesso", False))
        },
        "forcar_troca_senha": precisa_trocar_senha
    }), 200
# -------------------------
# Me
# -------------------------

@auth_bp.route("/me", methods=["GET"])
def me():
    usuario = get_usuario_logado()
    if not usuario:
        return jsonify({"error": "Não autenticado."}), 401

    cliente = Cliente.query.get(usuario.cliente_id)
    if not cliente:
        return jsonify({"error": "Cliente não encontrado."}), 404

    assinatura = cliente.assinatura
    tipo_usuario = usuario.tipo.value if hasattr(usuario.tipo, "value") else str(usuario.tipo).lower()

    return jsonify({
        "user": {
            "id": usuario.id,
            "nome": usuario.nome_completo,
            "email": usuario.email,
            "tipo": tipo_usuario,
            "ativo": bool(usuario.ativo)
        },
        "empresa": {
            "id": cliente.id,
            "nome": cliente.nome_empresa,
            "cnpj": cliente.cnpj
        },
        "assinatura": {
            "status": assinatura.status.value if assinatura else None,
            "provider_status": assinatura.provider_status if assinatura else None,
            "trial_ends_at": assinatura.trial_ends_at.isoformat() if assinatura and assinatura.trial_ends_at else None
        },
        "seguranca": {
            "ultimo_login": usuario.ultimo_login.isoformat() if usuario.ultimo_login else None,
            "ultimo_ip": usuario.ultimo_ip,
            "ultimo_user_agent": usuario.ultimo_user_agent,
            "sessao_expira_em": usuario.sessao_expira_em.isoformat() if usuario.sessao_expira_em else None
        }
    }), 200

# -------------------------
# Listar usuários do cliente
# -------------------------

@auth_bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    usuario_logado, erro = require_master()
    if erro:
        return erro

    usuarios = Usuario.query.filter_by(
        cliente_id=usuario_logado.cliente_id
    ).order_by(Usuario.id.asc()).all()

    resultado = []
    for usuario in usuarios:
        resultado.append({
            "id": usuario.id,
            "nome": usuario.nome_completo,
            "email": usuario.email,
            "tipo": usuario.tipo.value,
            "ativo": bool(usuario.ativo)
        })

    total_ativos = Usuario.query.filter_by(
        cliente_id=usuario_logado.cliente_id,
        ativo=True
    ).count()

    return jsonify({
        "usuarios": resultado,
        "plano": {
            "limite_usuarios_ativos": LIMITE_USUARIOS_ATIVOS,
            "usuarios_ativos": total_ativos
        }
    }), 200


# -------------------------
# Criar usuário comum
# -------------------------

@auth_bp.route("/usuarios", methods=["POST"])
def criar_usuario_comum():
    usuario_logado, erro = require_master()
    if erro:
        return erro

    data = request.get_json(silent=True) or {}

    nome = (data.get("nome") or "").strip()
    email = (data.get("email") or "").strip().lower()
    senha = data.get("senha") or ""

    if not nome or not email or not senha:
        return jsonify({"error": "Nome, email e senha são obrigatórios."}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Formato de email inválido."}), 400

    if not is_strong_password(senha):
        return jsonify({
            "error": "A senha deve ter no mínimo 8 caracteres, incluindo letra maiúscula, letra minúscula, número e caractere especial."
        }), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({"error": "Este email já está cadastrado."}), 409

    total_usuarios_ativos = Usuario.query.filter_by(
        cliente_id=usuario_logado.cliente_id,
        ativo=True
    ).count()

    if total_usuarios_ativos >= LIMITE_USUARIOS_ATIVOS:
        return jsonify({
            "error": f"Seu plano permite no máximo {LIMITE_USUARIOS_ATIVOS} usuários ativos."
        }), 400

    try:
        novo_usuario = Usuario(
            cliente_id=usuario_logado.cliente_id,
            nome_completo=nome,
            email=email,
            tipo=TipoUsuario.COMUM,
            ativo=True
        )
        novo_usuario.set_password(senha)

        db.session.add(novo_usuario)
        db.session.commit()

        total_ativos_atualizado = Usuario.query.filter_by(
            cliente_id=usuario_logado.cliente_id,
            ativo=True
        ).count()

        return jsonify({
            "message": "Usuário comum criado com sucesso.",
            "usuario": {
                "id": novo_usuario.id,
                "nome": novo_usuario.nome_completo,
                "email": novo_usuario.email,
                "tipo": novo_usuario.tipo.value,
                "ativo": bool(novo_usuario.ativo)
            },
            "plano": {
                "limite_usuarios_ativos": LIMITE_USUARIOS_ATIVOS,
                "usuarios_ativos": total_ativos_atualizado
            }
        }), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao criar usuário comum")
        return jsonify({"error": "Erro ao criar usuário comum."}), 500

# -------------------------
# Ativar / desativar usuário comum
# -------------------------

@auth_bp.route("/usuarios/<int:usuario_id>/toggle", methods=["PATCH"])
def alternar_status_usuario(usuario_id):
    usuario_logado, erro = require_master()
    if erro:
        return erro

    usuario_alvo = Usuario.query.get(usuario_id)
    if not usuario_alvo:
        return jsonify({"error": "Usuário alvo não encontrado."}), 404

    if usuario_alvo.cliente_id != usuario_logado.cliente_id:
        return jsonify({"error": "Você não pode alterar usuários de outro cliente."}), 403

    if usuario_alvo.tipo == TipoUsuario.MASTER:
        return jsonify({"error": "Não é permitido ativar/desativar o usuário master por esta rota."}), 400

    try:
        usuario_alvo.ativo = not bool(usuario_alvo.ativo)
        db.session.commit()

        return jsonify({
            "message": "Status do usuário atualizado com sucesso.",
            "usuario": {
                "id": usuario_alvo.id,
                "nome": usuario_alvo.nome_completo,
                "email": usuario_alvo.email,
                "tipo": usuario_alvo.tipo.value,
                "ativo": bool(usuario_alvo.ativo)
            }
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao alternar status do usuário")
        return jsonify({"error": "Erro ao atualizar status do usuário."}), 500
    
# -------------------------
# Segurança da conta do usuário
# -------------------------

@auth_bp.route("/usuario/<int:usuario_id>/seguranca", methods=["GET"])
def seguranca_usuario(usuario_id):
    usuario_logado, erro = require_master()
    if erro:
        return erro

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"error": "Usuário não encontrado."}), 404

    if usuario.cliente_id != usuario_logado.cliente_id:
        return jsonify({"error": "Acesso negado."}), 403

    def formatar_data(data):
        if not data:
            return None
        return data.replace(tzinfo=timezone.utc).isoformat()

    return jsonify({
        "ultimo_login": formatar_data(usuario.ultimo_login),
        "ultimo_ip": usuario.ultimo_ip,
        "ultimo_user_agent": usuario.ultimo_user_agent,
        "sessao_expira_em": formatar_data(usuario.sessao_expira_em)
    }), 200


# -------------------------
# Forgot password
# -------------------------

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    rate_limit_key = f"{_get_client_ip()}:{email or 'sem-email'}"

    throttled = throttle_or_response("forgot_password", rate_limit_key)
    if throttled:
        return throttled

    if not email or not is_valid_email(email):
        return jsonify({"error": "Informe um e-mail válido."}), 400

    usuario = Usuario.query.filter_by(email=email).first()

    mensagem_padrao = {
        "message": "Se o e-mail estiver cadastrado, enviaremos um código de recuperação."
    }

    if not usuario or not usuario.ativo:
        return jsonify(mensagem_padrao), 200

    try:
        codigo = gerar_codigo_reset()

        usuario.reset_code = codigo
        usuario.reset_code_expires_at = datetime.utcnow() + timedelta(minutes=10)
        usuario.reset_code_used = False

        db.session.commit()

        enviar_codigo_recuperacao_senha(
            destinatario=usuario.email,
            nome_usuario=usuario.nome_completo,
            codigo=codigo
        )

        reset_rate_limit("forgot_password", rate_limit_key)
        return jsonify(mensagem_padrao), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao solicitar recuperação de senha")
        return jsonify({"error": "Erro ao processar a solicitação. Tente novamente mais tarde."}), 500


# -------------------------
# Verify reset code
# -------------------------

@auth_bp.route("/verify-reset-code", methods=["POST"])
def verify_reset_code():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    rate_limit_key = f"{_get_client_ip()}:{email or 'sem-email'}"

    throttled = throttle_or_response("verify_reset_code", rate_limit_key)
    if throttled:
        return throttled

    if not email or not code:
        return jsonify({"error": "E-mail e código são obrigatórios."}), 400

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario or not usuario.ativo:
        return jsonify({"error": "Código inválido ou expirado."}), 400

    if not usuario.reset_code or usuario.reset_code != code:
        return jsonify({"error": "Código inválido ou expirado."}), 400

    if usuario.reset_code_used:
        return jsonify({"error": "Código inválido ou expirado."}), 400

    if not usuario.reset_code_expires_at or usuario.reset_code_expires_at < datetime.utcnow():
        return jsonify({"error": "Código inválido ou expirado."}), 400

    reset_rate_limit("verify_reset_code", rate_limit_key)
    return jsonify({"message": "Código validado com sucesso."}), 200


# -------------------------
# Reset password
# -------------------------

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    nova_senha = data.get("nova_senha") or ""
    confirma_nova_senha = data.get("confirma_nova_senha") or ""
    rate_limit_key = f"{_get_client_ip()}:{email or 'sem-email'}"

    throttled = throttle_or_response("reset_password", rate_limit_key)
    if throttled:
        return throttled

    if not email or not code or not nova_senha or not confirma_nova_senha:
        return jsonify({"error": "Todos os campos são obrigatórios."}), 400

    if nova_senha != confirma_nova_senha:
        return jsonify({"error": "As senhas não coincidem."}), 400

    if not is_strong_password(nova_senha):
        return jsonify({
            "error": "A nova senha deve ter no mínimo 8 caracteres, incluindo letra maiúscula, letra minúscula, número e caractere especial."
        }), 400

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario or not usuario.ativo:
        return jsonify({"error": "Código inválido ou expirado."}), 400

    if not usuario.reset_code or usuario.reset_code != code:
        return jsonify({"error": "Código inválido ou expirado."}), 400

    if usuario.reset_code_used:
        return jsonify({"error": "Código inválido ou expirado."}), 400

    if not usuario.reset_code_expires_at or usuario.reset_code_expires_at < datetime.utcnow():
        return jsonify({"error": "Código inválido ou expirado."}), 400

    try:
        usuario.set_password(nova_senha)
        usuario.reset_code_used = True
        usuario.reset_code = None
        usuario.reset_code_expires_at = None

        db.session.commit()

        reset_rate_limit("reset_password", rate_limit_key)
        return jsonify({"message": "Senha redefinida com sucesso. Faça login com a nova senha."}), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao redefinir senha")
        return jsonify({"error": "Erro ao redefinir senha."}), 500


# -------------------------
# Logout
# -------------------------

@auth_bp.route("/logout", methods=["POST"])
def logout():
    usuario = None

    user_id = session.get("user_id")
    if user_id:
        usuario = Usuario.query.get(user_id)

    try:
        if usuario:
            usuario.session_token = None
            usuario.sessao_expira_em = None
            db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao limpar sessão no logout")

    session.clear()
    return jsonify({"message": "Logout bem-sucedido!"}), 200

# -------------------------
# Status
# -------------------------

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

    return jsonify({"logged_in": False}), 200
