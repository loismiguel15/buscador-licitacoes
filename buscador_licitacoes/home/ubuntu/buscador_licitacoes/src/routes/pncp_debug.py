from flask import Blueprint, request, jsonify
from datetime import date, timedelta
from src.services.pncp_client import fetch_contratacoes_publicacao

pncp_debug_bp = Blueprint("pncp_debug", __name__)

@pncp_debug_bp.route("/raw", methods=["GET"])
def raw_pncp():
    dias = int(request.args.get("dias", 3))
    limite = max(10, int(request.args.get("limite", 10)))
    codigo_modalidade = int(request.args.get("modalidade", 6))

    hoje = date.today()
    ini = (hoje - timedelta(days=dias)).strftime("%Y%m%d")
    fim = hoje.strftime("%Y%m%d")

    data = fetch_contratacoes_publicacao(
        data_inicial=ini,
        data_final=fim,
        codigo_modalidade=codigo_modalidade,
        pagina=1,
        tamanho=limite
    )

    # devolve só 1 item pra ficar leve
    itens = data.get("data", [])
    return jsonify({
        "periodo": {"dataInicial": ini, "dataFinal": fim},
        "total_recebidos": len(itens),
        "primeiro_item": itens[0] if itens else None
    })