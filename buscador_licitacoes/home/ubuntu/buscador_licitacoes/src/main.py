import os
import sys
from dotenv import load_dotenv
from src.services.acesso_service import cliente_tem_acesso

load_dotenv()

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify, session, redirect
from apscheduler.schedulers.background import BackgroundScheduler

from src.models import db
from src.services.monitoramento_service import processar_monitoramento

# Blueprints
from src.routes.auth import auth_bp
from src.routes.licitacao import licitacao_bp
from src.routes.pncp import pncp_bp
from src.routes.pncp_debug import pncp_debug_bp
from src.routes.preferencias import preferencias_bp
from src.routes.assinaturas import assinaturas_bp
from src.routes.webhooks import webhooks_bp
from src.routes.pagamento import pagamento_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "asdf#FGSgvasgf$5$WGT")

# ==========================
# Database config
# ==========================
database_url = os.getenv("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    print("🔥 USANDO POSTGRES:", database_url)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DB_PATH = os.path.join(BASE_DIR, "app.db")

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"timeout": 30}
    }

    print("⚠️ USANDO SQLITE LOCAL:", app.config["SQLALCHEMY_DATABASE_URI"])

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ==========================
# Init DB
# ==========================
db.init_app(app)
with app.app_context():
    db.create_all()

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
            print(f"[MONITORAMENTO OK] {resultado}")
        except Exception as e:
            db.session.rollback()
            print(f"[MONITORAMENTO ERRO] {e}")


def iniciar_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        func=job_monitoramento,
        trigger="cron",
        hour=8,
        minute=0,
        id="monitoramento_08h",
        replace_existing=True,
    )

    scheduler.add_job(
        func=job_monitoramento,
        trigger="cron",
        hour=12,
        minute=0,
        id="monitoramento_12h",
        replace_existing=True,
    )

    scheduler.add_job(
        func=job_monitoramento,
        trigger="cron",
        hour=16,
        minute=0,
        id="monitoramento_16h",
        replace_existing=True,
    )

    scheduler.start()
    print("[SCHEDULER] Monitoramento agendado para 08:00, 12:00 e 16:00")


# ==========================
# Rotas protegidas
# ==========================
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login.html")

    cliente_id = session.get("cliente_id")
    if not cliente_tem_acesso(cliente_id):
        return redirect("/assinatura.html")

    return send_from_directory(app.static_folder, "painel_admin.html")


@app.route("/resultados", methods=["GET"])
def resultados():
    if "user_id" not in session:
        return redirect("/login.html")

    cliente_id = session.get("cliente_id")
    if not cliente_tem_acesso(cliente_id):
        return redirect("/assinatura.html")

    return send_from_directory(app.static_folder, "resultados.html")


@app.route("/detalhes", methods=["GET"])
def detalhes():
    if "user_id" not in session:
        return redirect("/login.html")

    cliente_id = session.get("cliente_id")
    if not cliente_tem_acesso(cliente_id):
        return redirect("/assinatura.html")

    return send_from_directory(app.static_folder, "detalhes_licitacao.html")


@app.route("/licitacoes_encontradas", methods=["GET"])
def licitacoes_encontradas():
    if "user_id" not in session:
        return redirect("/login.html")

    cliente_id = session.get("cliente_id")
    if not cliente_tem_acesso(cliente_id):
        return redirect("/assinatura.html")

    return send_from_directory(app.static_folder, "licitacoes_encontradas.html")


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
# Debug
# ==========================
@app.route("/debug/testar-download-edital/<int:licitacao_id>", methods=["GET"])
def debug_testar_download_edital(licitacao_id):
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


if __name__ == "__main__":
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "0") == "1"

    if enable_scheduler:
        iniciar_scheduler()
    else:
        print("[SCHEDULER] Desativado. Use /api/pncp-debug/monitorar para testar manualmente.")

    app.run(host="0.0.0.0", port=5000, debug=False)