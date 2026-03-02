import os
import sys

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from src.models import db
from src.routes.auth import auth_bp
from src.routes.licitacao import licitacao_bp
from src.routes.pncp import pncp_bp
from src.routes.pncp_debug import pncp_debug_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config["SECRET_KEY"] = "asdf#FGSgvasgf$5$WGT"

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(licitacao_bp, url_prefix="/api/licitacoes")

# ==========================
# Database config (SQLite by default)
# ==========================
# Use SQLite by default (best for local dev on Windows).
# To use MySQL later, set USE_SQLITE=0 and configure DB_* env vars.
use_sqlite = os.getenv("USE_SQLITE", "1") == "1"

if use_sqlite:
    # Creates app.db in the project root (same folder where you run the command)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '3306')}/"
        f"{os.getenv('DB_NAME', 'mydb')}"
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.register_blueprint(pncp_bp, url_prefix="/api/pncp")
app.register_blueprint(pncp_debug_bp, url_prefix="/api/pncp")

db.init_app(app)
with app.app_context():
    db.create_all()


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)