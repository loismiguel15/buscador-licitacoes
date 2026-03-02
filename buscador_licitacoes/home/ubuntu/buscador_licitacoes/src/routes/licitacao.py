from flask import Blueprint, request, jsonify, session
from src.models import db, Licitacao
from sqlalchemy import and_, or_
from datetime import datetime

licitacao_bp = Blueprint("licitacao", __name__)

# Helper to convert Licitacao object to dictionary
def licitacao_to_dict(licitacao: Licitacao):
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
        # "texto_integral_aviso": licitacao.texto_integral_aviso,  # manter fora da listagem
        "valor_estimado": float(licitacao.valor_estimado) if licitacao.valor_estimado is not None else None,
        "situacao": licitacao.situacao,
        "data_coleta": licitacao.data_coleta.isoformat() if licitacao.data_coleta else None,
        "data_ultima_atualizacao": licitacao.data_ultima_atualizacao.isoformat() if licitacao.data_ultima_atualizacao else None,
    }


@licitacao_bp.route("/buscar", methods=["GET"])
def buscar_licitacoes():
    # Params
    palavra_chave = request.args.get("palavra_chave", default=None, type=str)
    modalidade = request.args.get("modalidade", default=None, type=str)
    orgao = request.args.get("orgao", default=None, type=str)
    uf = request.args.get("uf", default=None, type=str)

    page = request.args.get("page", default=1, type=int)

    # evita abuso: per_page entre 1 e 50
    per_page = request.args.get("per_page", default=10, type=int)
    per_page = max(1, min(per_page, 50))

    # Build query
    query = Licitacao.query
    filters = []

    if palavra_chave:
        like = f"%{palavra_chave}%"
        filters.append(
            or_(
                Licitacao.objeto.ilike(like),
                Licitacao.orgao_licitante.ilike(like),
                Licitacao.numero_processo.ilike(like),
                Licitacao.modalidade.ilike(like),
            )
        )

    if modalidade:
        filters.append(Licitacao.modalidade.ilike(f"%{modalidade}%"))

    if orgao:
        filters.append(Licitacao.orgao_licitante.ilike(f"%{orgao}%"))

    if uf:
        filters.append(Licitacao.localidade_uf.ilike(f"%{uf}%"))

    if filters:
        query = query.filter(and_(*filters))

    # Order: mais recente primeiro
    query = query.order_by(Licitacao.data_publicacao.desc().nullslast(), Licitacao.id.desc())

    try:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        resultados = [licitacao_to_dict(lic) for lic in pagination.items]

        return jsonify({
            "message": "Busca realizada com sucesso",
            "resultados": resultados,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": max(1, pagination.pages),
            }
        }), 200

    except Exception as e:
        print(f"Error during search: {e}")
        return jsonify({"error": "Erro ao realizar a busca."}), 500


@licitacao_bp.route("/limpar-teste", methods=["POST"])
def limpar_licitacoes_teste():
    """
    Remove licitações com fonte_dados = 'TESTE'
    (pra não misturar com dados reais do PNCP)
    """
    try:
        deleted = Licitacao.query.filter(Licitacao.fonte_dados == "TESTE").delete()
        db.session.commit()
        return jsonify({
            "message": "Licitações de teste removidas com sucesso",
            "removidos": deleted
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting TESTE: {e}")
        return jsonify({"error": "Erro ao remover licitações de teste."}), 500


@licitacao_bp.route("/<int:licitacao_id>", methods=["GET"])
def get_licitacao_detalhes(licitacao_id):
    try:
        licitacao = Licitacao.query.get(licitacao_id)

        if not licitacao:
            return jsonify({"error": "Licitação não encontrada."}), 404

        result_dict = licitacao_to_dict(licitacao)
        result_dict["texto_integral_aviso"] = licitacao.texto_integral_aviso

        return jsonify({
            "message": "Detalhes da licitação obtidos com sucesso",
            "licitacao": result_dict
        }), 200

    except Exception as e:
        print(f"Error fetching details for ID {licitacao_id}: {e}")
        return jsonify({"error": "Erro ao obter detalhes da licitação."}), 500