import re
import unicodedata
from datetime import datetime

from flask import Blueprint, request, jsonify, session, send_file, redirect
from sqlalchemy import and_, or_, case, func
from rapidfuzz import fuzz

from src.models import db, Licitacao, LicitacaoCliente
from src.services.edital_service import baixar_edital_em_memoria
from src.routes._session_guard import login_required, assinatura_required

licitacao_bp = Blueprint("licitacao", __name__)


def remover_acentos(texto):
    if not texto:
        return ""

    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).lower()


def texto_parecido(texto, termo, limite=90):
    if not texto or not termo:
        return False

    texto = remover_acentos(texto)
    termo = remover_acentos(termo)

    score1 = fuzz.partial_ratio(texto, termo)
    score2 = fuzz.token_sort_ratio(texto, termo)

    return max(score1, score2) >= limite


def licitacao_to_dict(lic):
    return {
        "id": lic.id,
        "numero_processo": lic.numero_processo,
        "identificador_unico_pncp": lic.identificador_unico_pncp,
        "orgao_licitante": lic.orgao_licitante,
        "modalidade": lic.modalidade,
        "objeto": lic.objeto,
        "data_publicacao": lic.data_publicacao.isoformat() if lic.data_publicacao else None,
        "data_abertura_propostas": lic.data_abertura_propostas.isoformat() if lic.data_abertura_propostas else None,
        "data_encerramento_proposta": lic.data_encerramento_proposta.isoformat() if lic.data_encerramento_proposta else None,
        "localidade_uf": lic.localidade_uf,
        "localidade_municipio": lic.localidade_municipio,
        "fonte_dados": lic.fonte_dados,
        "link_fonte": lic.link_fonte,
        "link_edital": lic.link_edital,
        "caminho_edital": lic.caminho_edital,
        "texto_integral_aviso": lic.texto_integral_aviso,
        "valor_estimado": float(lic.valor_estimado) if lic.valor_estimado is not None else None,
        "situacao": lic.situacao,
        "data_coleta": lic.data_coleta.isoformat() if lic.data_coleta else None,
        "data_ultima_atualizacao": lic.data_ultima_atualizacao.isoformat() if lic.data_ultima_atualizacao else None,
    }


@licitacao_bp.route("/buscar", methods=["GET"])
@login_required
@assinatura_required
def buscar_licitacoes():
    palavra_chave = request.args.get("palavra_chave", default=None, type=str)
    if not palavra_chave:
        palavra_chave = request.args.get("palavra", default=None, type=str)

    modalidade = request.args.get("modalidade", default=None, type=str)
    orgao = request.args.get("orgao", default=None, type=str)
    uf = request.args.get("uf", default=None, type=str)
    data_inicio = request.args.get("data_inicio", default=None, type=str)

    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)
    per_page = max(1, min(per_page, 50))

    query = Licitacao.query
    filters = []
    palavras = []
    dt_inicio = None

    if palavra_chave:
        palavra_chave = palavra_chave.strip()

        stopwords = {
            "e", "de", "da", "do", "das", "dos",
            "para", "com", "em", "a", "o", "as", "os"
        }

        palavras = [
            p.strip()
            for p in re.split(r"[,\s]+", palavra_chave)
            if p.strip() and p.strip().lower() not in stopwords
        ]

        filtros_palavras = []
        for palavra in palavras:
            like = f"%{palavra}%"
            filtros_palavras.append(
                or_(
                    Licitacao.objeto.ilike(like),
                    Licitacao.orgao_licitante.ilike(like),
                    Licitacao.numero_processo.ilike(like),
                    Licitacao.modalidade.ilike(like),
                    Licitacao.localidade_municipio.ilike(like),
                )
            )

        if filtros_palavras:
            filters.append(and_(*filtros_palavras))

    if modalidade:
        modalidade = modalidade.strip()
        if modalidade:
            filters.append(Licitacao.modalidade.ilike(f"%{modalidade}%"))

    if orgao:
        orgao = orgao.strip()
        if orgao:
            filters.append(Licitacao.orgao_licitante.ilike(f"%{orgao}%"))

    if uf:
        uf = uf.strip().upper()
        if uf:
            filters.append(Licitacao.localidade_uf == uf)

    try:
        if data_inicio:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            filters.append(func.date(Licitacao.data_publicacao) == dt_inicio)
    except ValueError:
        return jsonify({
            "error": "Formato de data inválido. Use YYYY-MM-DD."
        }), 400

    if filters:
        query = query.filter(and_(*filters))

    if palavras:
        relevancia = 0
        for palavra in palavras:
            like = f"%{palavra}%"
            relevancia += case((Licitacao.objeto.ilike(like), 10), else_=0)
            relevancia += case((Licitacao.orgao_licitante.ilike(like), 5), else_=0)
            relevancia += case((Licitacao.modalidade.ilike(like), 3), else_=0)
            relevancia += case((Licitacao.numero_processo.ilike(like), 2), else_=0)
            relevancia += case((Licitacao.localidade_municipio.ilike(like), 2), else_=0)

        query = query.order_by(
            relevancia.desc(),
            Licitacao.data_publicacao.desc(),
            Licitacao.id.desc()
        )
    else:
        query = query.order_by(
            Licitacao.data_publicacao.desc(),
            Licitacao.id.desc()
        )

    try:
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        itens = pagination.items

        if not itens and palavra_chave and len(palavras) == 1:
            consulta_ampla = Licitacao.query

            if modalidade:
                consulta_ampla = consulta_ampla.filter(
                    Licitacao.modalidade.ilike(f"%{modalidade}%")
                )

            if orgao:
                consulta_ampla = consulta_ampla.filter(
                    Licitacao.orgao_licitante.ilike(f"%{orgao}%")
                )

            if uf:
                consulta_ampla = consulta_ampla.filter(
                    Licitacao.localidade_uf == uf
                )

            if dt_inicio:
                consulta_ampla = consulta_ampla.filter(
                    func.date(Licitacao.data_publicacao) == dt_inicio
                )

            candidatos = consulta_ampla.order_by(
                Licitacao.data_publicacao.desc(),
                Licitacao.id.desc()
            ).limit(300).all()

            itens_parecidos = []
            for lic in candidatos:
                if (
                    texto_parecido(lic.objeto or "", palavra_chave) or
                    texto_parecido(lic.orgao_licitante or "", palavra_chave) or
                    texto_parecido(lic.modalidade or "", palavra_chave) or
                    texto_parecido(lic.numero_processo or "", palavra_chave) or
                    texto_parecido(lic.localidade_municipio or "", palavra_chave)
                ):
                    itens_parecidos.append(lic)

            def pontuar_licitacao(lic):
                score = 0
                termo = palavra_chave or ""

                if texto_parecido(lic.objeto or "", termo):
                    score += 10
                if texto_parecido(lic.orgao_licitante or "", termo):
                    score += 5
                if texto_parecido(lic.modalidade or "", termo):
                    score += 3
                if texto_parecido(lic.numero_processo or "", termo):
                    score += 2
                if texto_parecido(lic.localidade_municipio or "", termo):
                    score += 2

                return score

            itens_parecidos.sort(
                key=lambda lic: (
                    pontuar_licitacao(lic),
                    lic.data_publicacao or "",
                    lic.id or 0
                ),
                reverse=True
            )

            total_similares = len(itens_parecidos)
            inicio = (page - 1) * per_page
            fim = inicio + per_page
            itens = itens_parecidos[inicio:fim]

            resultados = [licitacao_to_dict(lic) for lic in itens]

            total_pages = (total_similares + per_page - 1) // per_page
            total_pages = max(1, total_pages)

            return jsonify({
                "message": "Busca realizada com sucesso",
                "resultados": resultados,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_items": total_similares,
                    "total_pages": total_pages,
                }
            }), 200

        resultados = [licitacao_to_dict(lic) for lic in itens]

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
        print(f"Erro na busca: {e}")
        return jsonify({
            "error": "Erro ao realizar a busca."
        }), 500


@licitacao_bp.route("/minhas", methods=["GET"])
@login_required
@assinatura_required
def minhas_licitacoes():
    cliente_id = session.get("cliente_id")

    if not cliente_id:
        return jsonify({
            "error": "Usuário não autenticado"
        }), 401

    palavra_chave = request.args.get("palavra_chave", default=None, type=str)
    if not palavra_chave:
        palavra_chave = request.args.get("palavra", default=None, type=str)

    modalidade = request.args.get("modalidade", default=None, type=str)
    orgao = request.args.get("orgao", default=None, type=str)
    uf = request.args.get("uf", default=None, type=str)
    data_inicio = request.args.get("data_inicio", default=None, type=str)

    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    per_page = max(1, min(per_page, 50))

    query = (
        db.session.query(Licitacao)
        .join(LicitacaoCliente, LicitacaoCliente.licitacao_id == Licitacao.id)
        .filter(LicitacaoCliente.cliente_id == cliente_id)
    )

    filters = []
    palavras = []

    if palavra_chave:
        palavra_chave = palavra_chave.strip()

        stopwords = {
            "e", "de", "da", "do", "das", "dos",
            "para", "com", "em", "a", "o", "as", "os"
        }

        palavras = [
            p.strip()
            for p in re.split(r"[,\s]+", palavra_chave)
            if p.strip() and p.strip().lower() not in stopwords
        ]

        filtros_palavras = []
        for palavra in palavras:
            like = f"%{palavra}%"
            filtros_palavras.append(
                or_(
                    Licitacao.objeto.ilike(like),
                    Licitacao.orgao_licitante.ilike(like),
                    Licitacao.numero_processo.ilike(like),
                    Licitacao.modalidade.ilike(like),
                    Licitacao.localidade_municipio.ilike(like),
                )
            )

        if filtros_palavras:
            filters.append(and_(*filtros_palavras))

    if modalidade:
        modalidade = modalidade.strip()
        if modalidade:
            filters.append(Licitacao.modalidade.ilike(f"%{modalidade}%"))

    if orgao:
        orgao = orgao.strip()
        if orgao:
            filters.append(Licitacao.orgao_licitante.ilike(f"%{orgao}%"))

    if uf:
        uf = uf.strip().upper()
        if uf:
            filters.append(Licitacao.localidade_uf == uf)

    try:
        if data_inicio:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            filters.append(func.date(Licitacao.data_publicacao) == dt_inicio)
    except ValueError:
        return jsonify({
            "error": "Formato de data inválido. Use YYYY-MM-DD."
        }), 400

    if filters:
        query = query.filter(and_(*filters))

    if palavras:
        relevancia = 0
        for palavra in palavras:
            like = f"%{palavra}%"
            relevancia += case((Licitacao.objeto.ilike(like), 10), else_=0)
            relevancia += case((Licitacao.orgao_licitante.ilike(like), 5), else_=0)
            relevancia += case((Licitacao.modalidade.ilike(like), 3), else_=0)
            relevancia += case((Licitacao.numero_processo.ilike(like), 2), else_=0)
            relevancia += case((Licitacao.localidade_municipio.ilike(like), 2), else_=0)

        query = query.order_by(
            relevancia.desc(),
            LicitacaoCliente.data_encontro.desc(),
            Licitacao.data_publicacao.desc(),
            Licitacao.id.desc()
        )
    else:
        query = query.order_by(
            LicitacaoCliente.data_encontro.desc(),
            Licitacao.data_publicacao.desc(),
            Licitacao.id.desc()
        )

    try:
        print("========== FILTRO MINHAS ==========")
        print("cliente_id:", cliente_id)
        print("palavra_chave:", palavra_chave)
        print("uf:", uf)
        print("modalidade:", modalidade)
        print("data_inicio:", data_inicio)
        print("total filtrado:", query.count())
        print("===================================")

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        resultados = [licitacao_to_dict(lic) for lic in pagination.items]

        return jsonify({
            "message": "Licitações do cliente",
            "resultados": resultados,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": max(1, pagination.pages),
            }
        })

    except Exception as e:
        print(f"Erro em /minhas: {e}")
        return jsonify({
            "error": "Erro ao realizar a busca."
        }), 500


@licitacao_bp.route("/limpar-teste", methods=["POST"])
@login_required
@assinatura_required
def limpar_licitacoes_teste():
    try:
        deleted = Licitacao.query.filter(
            Licitacao.fonte_dados == "TESTE"
        ).delete()

        db.session.commit()

        return jsonify({
            "message": "Licitações de teste removidas",
            "removidos": deleted
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao limpar testes: {e}")

        return jsonify({
            "error": "Erro ao remover licitações de teste."
        }), 500


@licitacao_bp.route("/visualizar-edital/<int:licitacao_id>", methods=["GET"])
@login_required
@assinatura_required
def visualizar_edital(licitacao_id):
    try:
        lic = Licitacao.query.get(licitacao_id)

        if not lic:
            return jsonify({"error": "Licitação não encontrada."}), 404

        url_edital = lic.link_edital or lic.link_fonte

        if not url_edital:
            return jsonify({"error": "Edital não disponível para visualização."}), 404

        return redirect(url_edital)

    except Exception as e:
        print(f"Erro ao visualizar edital {licitacao_id}: {e}")
        return jsonify({"error": "Erro ao visualizar edital."}), 500


@licitacao_bp.route("/baixar-edital/<int:licitacao_id>", methods=["GET"])
@login_required
@assinatura_required
def baixar_edital_licitacao(licitacao_id):
    try:
        lic = Licitacao.query.get(licitacao_id)

        if not lic:
            return jsonify({"error": "Licitação não encontrada."}), 404

        url_edital = lic.link_edital or lic.link_fonte
        identificador = (
            lic.identificador_unico_pncp
            or lic.numero_processo
            or f"licitacao_{lic.id}"
        )

        if not url_edital:
            return jsonify({"error": "Esta licitação não possui link de edital."}), 400

        arquivo, nome_arquivo = baixar_edital_em_memoria(url_edital, identificador)

        if not arquivo:
            return jsonify({"error": "Não foi possível baixar o edital."}), 400

        return send_file(
            arquivo,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nome_arquivo
        )

    except Exception as e:
        print(f"Erro ao baixar edital {licitacao_id}: {e}")
        return jsonify({"error": "Erro ao baixar edital."}), 500


@licitacao_bp.route("/<int:licitacao_id>", methods=["GET"])
@login_required
@assinatura_required
def get_licitacao_detalhes(licitacao_id):
    try:
        licitacao = Licitacao.query.get(licitacao_id)

        if not licitacao:
            return jsonify({
                "error": "Licitação não encontrada."
            }), 404

        result_dict = licitacao_to_dict(licitacao)
        result_dict["texto_integral_aviso"] = licitacao.texto_integral_aviso

        return jsonify({
            "message": "Detalhes obtidos",
            "licitacao": result_dict
        }), 200

    except Exception as e:
        print(f"Erro ao buscar detalhes {licitacao_id}: {e}")

        return jsonify({
            "error": "Erro ao obter detalhes da licitação."
        }), 500