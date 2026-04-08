import os
import secrets
import sys
import traceback
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.acesso_service import cliente_tem_acesso

from flask import Flask, send_from_directory, jsonify, session, redirect, request, current_app
from apscheduler.schedulers.background import BackgroundScheduler

from src.models import db
from src.services.monitoramento_service import (
    processar_monitoramento,
    buscar_licitacoes_para_cliente,
    _obter_registro_execucao,
)

# Blueprints
from src.routes.auth import auth_bp
from src.routes.licitacao import licitacao_bp
from src.routes.pncp import pncp_bp
from src.routes.pncp_debug import pncp_debug_bp
from src.routes.preferencias import preferencias_bp
from src.routes.assinaturas import assinaturas_bp
from src.routes.webhooks import webhooks_bp
from src.routes.pagamento import pagamento_bp
from src.routes._session_guard import assinatura_required_page

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
if not os.getenv("SECRET_KEY"):
    app.logger.warning("SECRET_KEY não configurada via ambiente. Usando chave efêmera apenas para esta execução.")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

# ==========================
# Database config
# ==========================
database_url = os.getenv("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_timeout": 30,
        "max_overflow": 10,
        "connect_args": {
            "sslmode": "require",
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    }

    app.logger.info("Usando Postgres configurado por DATABASE_URL")
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DB_PATH = os.path.join(BASE_DIR, "app.db")

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"timeout": 30}
    }

    app.logger.warning("Usando SQLite local em %s", app.config["SQLALCHEMY_DATABASE_URI"])

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ==========================
# Init DB
# ==========================
db.init_app(app)
with app.app_context():
    db.create_all()


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PUBLIC_CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/verify-reset-code",
    "/api/auth/reset-password",
}
AUTHENTICATED_CSRF_EXEMPT_PATHS = {
    "/api/auth/logout",
}


def _same_origin(valor_origem: str) -> bool:
    if not valor_origem:
        return False

    origem_limpa = valor_origem.rstrip("/")
    base_url = request.host_url.rstrip("/")
    return origem_limpa == base_url


@app.before_request
def protect_authenticated_requests():
    if request.method in SAFE_METHODS:
        return None

    if request.path.startswith("/api/webhooks/"):
        return None

    if request.path in AUTHENTICATED_CSRF_EXEMPT_PATHS:
        return None

    if request.path in PUBLIC_CSRF_EXEMPT_PATHS and "user_id" not in session:
        return None

    if "user_id" not in session:
        return None

    origem = request.headers.get("Origin")
    referer = request.headers.get("Referer")

    if origem and _same_origin(origem):
        return None

    if referer:
        referer_base = referer.split("/", 3)
        if len(referer_base) >= 3:
            if _same_origin("/".join(referer_base[:3])):
                return None

    current_app.logger.warning(
        "Requisição bloqueada por validação de origem. path=%s method=%s origin=%s referer=%s",
        request.path,
        request.method,
        origem,
        referer,
    )
    return jsonify({"error": "Requisição bloqueada por segurança."}), 403

# ==========================
# Register Blueprints
# ==========================
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(licitacao_bp, url_prefix="/api/licitacoes")
app.register_blueprint(pncp_bp, url_prefix="/api/pncp")
app.register_blueprint(pncp_debug_bp, url_prefix="/api/pncp-debug")
app.register_blueprint(preferencias_bp)
app.register_blueprint(assinaturas_bp)
app.register_blueprint(webhooks_bp)
app.register_blueprint(pagamento_bp)

# ==========================
# Scheduler
# ==========================
scheduler = BackgroundScheduler(
    timezone="America/Sao_Paulo",
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
    },
)


def job_monitoramento():
    with app.app_context():
        try:
            resultado = processar_monitoramento()
            app.logger.info("Monitoramento executado com sucesso: %s", resultado)
        except Exception:
            db.session.rollback()
            app.logger.exception("Erro durante monitoramento agendado")


def iniciar_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        func=job_monitoramento,
        trigger="cron",
        hour="8,10,12,14,16,18",
        minute=0,
        id="monitoramento_recorrente",
        replace_existing=True,
    )

    scheduler.start()
    app.logger.info("Monitoramento agendado para 08:00, 10:00, 12:00, 14:00, 16:00 e 18:00")


# ==========================
# Rotas protegidas
# ==========================
@app.route("/dashboard", methods=["GET"])
@assinatura_required_page
def dashboard():
    return send_from_directory(app.static_folder, "painel_admin.html")


@app.route("/resultados", methods=["GET"])
@assinatura_required_page
def resultados():
    return send_from_directory(app.static_folder, "resultados.html")


@app.route("/detalhes", methods=["GET"])
@assinatura_required_page
def detalhes():
    return send_from_directory(app.static_folder, "detalhes_licitacao.html")


@app.route("/licitacoes_encontradas", methods=["GET"])
@assinatura_required_page
def licitacoes_encontradas():
    return send_from_directory(app.static_folder, "licitacoes_encontradas.html")


# ==========================
# Debug leve
# ==========================
@app.route("/debug-db", methods=["GET"])
def debug_db():
    if os.getenv("ENABLE_DEBUG_ROUTES", "0") != "1":
        return jsonify({"error": "Endpoint não encontrado."}), 404

    try:
        registro = _obter_registro_execucao()

        return jsonify({
            "ok": True,
            "ultima_execucao": registro.ultima_execucao.isoformat() if registro.ultima_execucao else None
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro em /debug-db")
        return jsonify({
            "ok": False,
            "erro": "Erro interno ao consultar debug."
        }), 500


@app.route("/debug-busca-manual", methods=["GET"])
def debug_busca_manual():
    if os.getenv("ENABLE_DEBUG_ROUTES", "0") != "1":
        return jsonify({"error": "Endpoint não encontrado."}), 404

    try:
        from src.models import Cliente

        cliente = Cliente.query.filter_by(ativo=True).first()
        if not cliente:
            return jsonify({
                "ok": False,
                "erro": "Nenhum cliente ativo encontrado"
            }), 404

        licitacoes = buscar_licitacoes_para_cliente(cliente, None)

        return jsonify({
            "ok": True,
            "cliente_id": cliente.id,
            "empresa": cliente.nome_empresa,
            "quantidade": len(licitacoes),
            "ids": [lic.id for lic in licitacoes[:10]]
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro em /debug-busca-manual")
        return jsonify({
            "ok": False,
            "erro": "Erro interno ao executar debug."
        }), 500


# ==========================
# Static / SPA fallback
# NÃO capturar /api/*
# ==========================
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path.startswith("api/"):
        return jsonify({"error": "Endpoint não encontrado."}), 404

    if path == "dashboard":
        return redirect("/dashboard")

    if path == "resultados":
        return redirect("/resultados")

    if path == "detalhes":
        return redirect("/detalhes")

    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    file_path = os.path.join(static_folder_path, path)
    if path != "" and os.path.exists(file_path):
        return send_from_directory(static_folder_path, path)

    index_path = os.path.join(static_folder_path, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(static_folder_path, "index.html")

    return "index.html not found", 404


# ==========================
# Debug edital
# ==========================
@app.route("/debug/testar-download-edital/<int:licitacao_id>", methods=["GET"])
def debug_testar_download_edital(licitacao_id):
    if os.getenv("ENABLE_DEBUG_ROUTES", "0") != "1":
        return jsonify({"error": "Endpoint não encontrado."}), 404

    from src.models import Licitacao
    from src.services.edital_service import baixar_edital

    lic = Licitacao.query.get(licitacao_id)
    if not lic:
        return {"erro": "Licitação não encontrada"}, 404

    resultado = baixar_edital(
        lic.link_edital,
        lic.identificador_unico_pncp
    )

    return {
        "id": lic.id,
        "identificador": lic.identificador_unico_pncp,
        "link_edital": lic.link_edital,
        "caminho_antes": lic.caminho_edital,
        "resultado_download": resultado,
        "root_path": app.root_path,
    }, 200


# ==========================
# Main
# ==========================
if __name__ == "__main__":
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "0") == "1"

    if enable_scheduler:
        iniciar_scheduler()
    else:
        app.logger.info("Scheduler desativado. Use /api/pncp-debug/monitorar para testar manualmente.")

    app.run(host="0.0.0.0", port=5000, debug=False)
