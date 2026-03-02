from flask import Blueprint, request, jsonify
from datetime import datetime, date, timedelta

from src.models import db, Licitacao
from src.services.pncp_client import fetch_contratacoes_publicacao

pncp_bp = Blueprint("pncp", __name__)

@pncp_bp.route("/sync", methods=["GET"])
def sync_pncp():
    try:
        dias = int(request.args.get("dias", 3))
        limite_total = int(request.args.get("limite", 200))  # total máximo desejado
        codigo_modalidade = int(request.args.get("modalidade", 6))

        hoje = date.today()
        ini = (hoje - timedelta(days=dias)).strftime("%Y%m%d")
        fim = hoje.strftime("%Y%m%d")

        salvos = 0
        atualizados = 0
        pulados = 0
        recebidos = 0

        pagina = 1
        tamanho_pagina = 50  # tamanho por requisição

        while recebidos < limite_total:

            data = fetch_contratacoes_publicacao(
                data_inicial=ini,
                data_final=fim,
                codigo_modalidade=codigo_modalidade,
                pagina=pagina,
                tamanho=tamanho_pagina
            )

            itens = data.get("data", [])

            if not itens:
                break  # acabou as páginas

            for it in itens:

                if recebidos >= limite_total:
                    break

                recebidos += 1

                pncp_id = it.get("numeroControlePNCP")
                if not pncp_id:
                    pulados += 1
                    continue

                objeto = (it.get("objetoCompra") or "").strip()
                orgao_ent = it.get("orgaoEntidade") or {}
                orgao = (orgao_ent.get("razaoSocial") or "").strip()

                if not objeto or not orgao:
                    pulados += 1
                    continue

                with db.session.no_autoflush:
                    lic = Licitacao.query.filter_by(
                        identificador_unico_pncp=str(pncp_id)
                    ).first()

                novo = lic is None

                if novo:
                    lic = Licitacao(
                        identificador_unico_pncp=str(pncp_id),
                        data_coleta=datetime.now(),
                        data_ultima_atualizacao=datetime.now(),
                    )

                unidade = it.get("unidadeOrgao") or {}

                lic.fonte_dados = "PNCP"
                lic.numero_processo = it.get("processo") or it.get("numeroCompra")
                lic.objeto = objeto
                lic.orgao_licitante = orgao
                lic.modalidade = it.get("modalidadeNome")
                lic.localidade_uf = unidade.get("ufSigla")
                lic.localidade_municipio = unidade.get("municipioNome")
                lic.valor_estimado = it.get("valorTotalEstimado")
                lic.situacao = it.get("situacaoCompraNome") or "N/D"
                lic.link_fonte = it.get("linkProcessoEletronico")

                lic.texto_integral_aviso = (
                    f"{lic.modalidade} | {lic.situacao} | PNCP: {pncp_id}\n"
                    f"Órgão: {orgao}\n"
                    f"Objeto: {objeto}"
                )

                dp = it.get("dataPublicacaoPncp")
                if dp:
                    try:
                        lic.data_publicacao = date.fromisoformat(dp[:10])
                    except:
                        lic.data_publicacao = date.today()

                dap = it.get("dataAberturaProposta")
                if dap:
                    try:
                        lic.data_abertura_propostas = datetime.fromisoformat(dap)
                    except:
                        pass

                lic.data_ultima_atualizacao = datetime.now()

                if novo:
                    db.session.add(lic)
                    salvos += 1
                else:
                    atualizados += 1

            pagina += 1

        db.session.commit()

        return jsonify({
            "message": "Sync PNCP concluído",
            "dias": dias,
            "modalidade": codigo_modalidade,
            "recebidos": recebidos,
            "salvos": salvos,
            "atualizados": atualizados,
            "pulados": pulados
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500