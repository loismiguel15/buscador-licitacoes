from flask import Blueprint, request, jsonify, session
from src.models import db, Licitacao
from sqlalchemy import or_, and_
from datetime import datetime

licitacao_bp = Blueprint("licitacao", __name__)

# Helper to convert Licitacao object to dictionary
def licitacao_to_dict(licitacao):
    return {
        "id": licitacao.id,
        "numero_processo": licitacao.numero_processo,
        "identificador_unico_pncp": licitacao.identificador_unico_pncp,
        "orgao_licitante": licitacao.orgao_licitante,
        "modalidade": licitacao.modalidade,
        "objeto": licitacao.objeto,
        "data_publicacao": licitacao.data_publicacao.isoformat() if licitacao.data_publicacao else None,
        "data_abertura_propostas": licitacao.data_abertura_propostas.isoformat() if licitacao.data_abertura_propostas else None,
        "localidade_uf": licitacao.localidade_uf,
        "localidade_municipio": licitacao.localidade_municipio,
        "fonte_dados": licitacao.fonte_dados,
        "link_fonte": licitacao.link_fonte,
        # "texto_integral_aviso": licitacao.texto_integral_aviso, # Avoid sending large text in list view
        "valor_estimado": float(licitacao.valor_estimado) if licitacao.valor_estimado is not None else None,
        "situacao": licitacao.situacao,
        "data_coleta": licitacao.data_coleta.isoformat() if licitacao.data_coleta else None,
        "data_ultima_atualizacao": licitacao.data_ultima_atualizacao.isoformat() if licitacao.data_ultima_atualizacao else None
    }

@licitacao_bp.route("/buscar", methods=["GET"])
def buscar_licitacoes():
    # Authentication check (optional, depending on requirements)
    # if "user_id" not in session:
    #     return jsonify({"error": "Acesso não autorizado"}), 401

    # Get query parameters
    palavra_chave = request.args.get("palavra_chave", default=None, type=str)
    modalidade = request.args.get("modalidade", default=None, type=str)
    orgao = request.args.get("orgao", default=None, type=str)
    uf = request.args.get("uf", default=None, type=str)
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    # Build query dynamically
    query = Licitacao.query
    filters = []

    if palavra_chave:
        # Simple search in 'objeto'. For better results, consider full-text search.
        filters.append(Licitacao.objeto.ilike(f"%{palavra_chave}%"))

    if modalidade:
        # Assuming 'modalidade' in the request matches the stored values
        filters.append(Licitacao.modalidade.ilike(f"%{modalidade}%"))

    if orgao:
        filters.append(Licitacao.orgao_licitante.ilike(f"%{orgao}%"))

    if uf:
        filters.append(Licitacao.localidade_uf.ilike(f"%{uf}%"))

    if filters:
        query = query.filter(and_(*filters))

    # Add ordering (e.g., by publication date descending)
    query = query.order_by(Licitacao.data_publicacao.desc().nullslast(), Licitacao.id.desc())

    # Paginate results
    try:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        licitacoes_paginadas = pagination.items
        total_items = pagination.total
        total_pages = pagination.pages

        resultados = [licitacao_to_dict(lic) for lic in licitacoes_paginadas]

        return jsonify({
            "message": "Busca realizada com sucesso",
            "resultados": resultados,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": total_pages
            }
        }), 200

    except Exception as e:
        print(f"Error during search: {e}") # Basic logging
        return jsonify({"error": "Erro ao realizar a busca."}), 500

@licitacao_bp.route("/<int:licitacao_id>", methods=["GET"])
def get_licitacao_detalhes(licitacao_id):
    # Authentication check (optional)
    # if "user_id" not in session:
    #     return jsonify({"error": "Acesso não autorizado"}), 401

    try:
        licitacao = Licitacao.query.get(licitacao_id)

        if not licitacao:
            return jsonify({"error": "Licitação não encontrada."}), 404

        # Include full text in detail view
        result_dict = licitacao_to_dict(licitacao)
        result_dict["texto_integral_aviso"] = licitacao.texto_integral_aviso

        return jsonify({
            "message": "Detalhes da licitação obtidos com sucesso",
            "licitacao": result_dict
        }), 200

    except Exception as e:
        print(f"Error fetching details for ID {licitacao_id}: {e}") # Basic logging
        return jsonify({"error": "Erro ao obter detalhes da licitação."}), 500

