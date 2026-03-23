from flask import Blueprint, request, jsonify
from datetime import date

from src.models import db
from src.services.pncp_client import fetch_contratacoes_publicacao
from src.services.licitacao_service import salvar_licitacao_pncp

pncp_bp = Blueprint("pncp", __name__)


@pncp_bp.route("/sync", methods=["GET"])
def sync_pncp():
    try:
        limite_total = int(request.args.get("limite", 200))
        codigo_modalidade_raw = request.args.get("modalidade")
        termo = request.args.get("termo")
        uf = request.args.get("uf")

        if codigo_modalidade_raw in (None, "", "null"):
            return jsonify({
                "error": (
                    "Para o endpoint /contratacoes/publicacao do PNCP, "
                    "o parâmetro 'modalidade' é obrigatório. "
                    "Exemplo: /api/pncp/sync?modalidade=8&uf=SP&limite=50"
                )
            }), 400

        codigo_modalidade = int(codigo_modalidade_raw)

        hoje = date.today()
        ini = hoje.strftime("%Y%m%d")
        fim = hoje.strftime("%Y%m%d")

        salvos = 0
        atualizados = 0
        pulados = 0
        recebidos = 0

        pagina = 1
        tamanho_pagina = 50

        while recebidos < limite_total:
            data = fetch_contratacoes_publicacao(
                data_inicial=ini,
                data_final=fim,
                codigo_modalidade=codigo_modalidade,
                pagina=pagina,
                tamanho=tamanho_pagina,
                uf=uf,
            )

            itens = data.get("data", []) or []

            if not itens:
                break

            for item in itens:
                if recebidos >= limite_total:
                    break

                recebidos += 1

                identificador = (
                    item.get("numeroControlePNCP")
                    or item.get("numeroCompra")
                    or item.get("sequencialCompra")
                )

                if not identificador:
                    pulados += 1
                    continue

                licitacao = salvar_licitacao_pncp(item)

                if not licitacao:
                    pulados += 1
                    continue

                if licitacao in db.session.new:
                    salvos += 1
                else:
                    atualizados += 1

            pagina += 1

        db.session.commit()

        return jsonify({
            "message": "Sync PNCP concluído",
            "modalidade": codigo_modalidade,
            "termo": termo,
            "uf": uf,
            "recebidos": recebidos,
            "salvos": salvos,
            "atualizados": atualizados,
            "pulados": pulados
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500