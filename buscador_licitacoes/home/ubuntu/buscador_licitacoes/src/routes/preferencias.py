from flask import Blueprint, request, jsonify, session
from datetime import datetime
from src.models import db, ClientePreferencias
from src.routes._session_guard import login_required

preferencias_bp = Blueprint("preferencias", __name__)


def _dedup_keep_order(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _keywords_to_csv(value, max_items=50):
    if value is None:
        return ""

    if isinstance(value, str):
        raw = value.replace(";", ",").split(",")
    elif isinstance(value, list):
        raw = value
    else:
        raw = [value]

    items = []
    for x in raw:
        s = str(x).strip().lower()
        if s:
            items.append(s)

    items = _dedup_keep_order(items)[:max_items]
    return ",".join(items)


def _ufs_to_csv(value, max_items=27):
    if value is None:
        return ""

    if isinstance(value, str):
        raw = value.replace(";", ",").split(",")
    elif isinstance(value, list):
        raw = value
    else:
        raw = [value]

    items = []
    for x in raw:
        s = str(x).strip().upper()
        if len(s) == 2 and s.isalpha():
            items.append(s)

    items = _dedup_keep_order(items)[:max_items]
    return ",".join(items)


def _modalidades_to_csv(value, max_items=50):
    if value is None:
        return ""

    if isinstance(value, str):
        raw = value.replace(";", ",").split(",")
    elif isinstance(value, list):
        raw = value
    else:
        raw = [value]

    items = []
    for x in raw:
        s = str(x).strip()
        if s and s.isdigit():
            items.append(s)

    items = _dedup_keep_order(items)[:max_items]
    return ",".join(items)


def _split_csv(s: str):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


@preferencias_bp.route("/api/preferencias", methods=["GET"])
@login_required
def get_preferencias():
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return jsonify({"error": "Sessão inválida (cliente_id não encontrado)."}), 401

    pref = ClientePreferencias.query.filter_by(cliente_id=cliente_id).first()

    if not pref:
        return jsonify({
            "cliente_id": cliente_id,
            "keywords": [],
            "ufs": [],
            "modalidades": [],
            "ativo": True,
            "updated_at": None
        }), 200

    return jsonify({
        "cliente_id": cliente_id,
        "keywords": _split_csv(pref.keywords),
        "ufs": _split_csv(pref.ufs),
        "modalidades": _split_csv(pref.modalidades),
        "ativo": bool(pref.ativo),
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
    }), 200


@preferencias_bp.route("/api/preferencias", methods=["POST"])
@login_required
def salvar_preferencias():
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return jsonify({"error": "Sessão inválida (cliente_id não encontrado)."}), 401

    if not request.is_json:
        return jsonify({"error": "Envie JSON no corpo da requisição."}), 400

    data = request.get_json(force=True) or {}

    keywords_csv = _keywords_to_csv(data.get("keywords"), max_items=50)
    ufs_csv = _ufs_to_csv(data.get("ufs"), max_items=27)
    modalidades_csv = _modalidades_to_csv(data.get("modalidades"), max_items=50)

    pref = ClientePreferencias.query.filter_by(cliente_id=cliente_id).first()
    if not pref:
        pref = ClientePreferencias(cliente_id=cliente_id)

    pref.keywords = keywords_csv
    pref.ufs = ufs_csv
    pref.modalidades = modalidades_csv
    pref.ativo = bool(data.get("ativo", True))
    pref.updated_at = datetime.utcnow()

    db.session.add(pref)
    db.session.commit()

    return jsonify({
        "message": "Preferências salvas com sucesso!",
        "cliente_id": cliente_id,
        "keywords": _split_csv(pref.keywords),
        "ufs": _split_csv(pref.ufs),
        "modalidades": _split_csv(pref.modalidades),
        "ativo": bool(pref.ativo),
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
    }), 200