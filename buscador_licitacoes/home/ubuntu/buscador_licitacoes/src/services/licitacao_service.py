from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.models import db, Licitacao, LicitacaoCliente
from src.services.pncp_client import descobrir_primeiro_pdf_pncp


def parse_data(data_str):
    if not data_str:
        return None

    formatos = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    valor = str(data_str).strip()

    for formato in formatos:
        try:
            if formato == "%Y-%m-%d":
                return datetime.strptime(valor[:10], formato)
            return datetime.strptime(valor[:26], formato)
        except ValueError:
            continue

    return None


def get_nested(data, *keys):
    """
    Tenta buscar um valor em vários caminhos possíveis do JSON.
    """
    for path in keys:
        valor = data
        try:
            for chave in path:
                if valor is None:
                    break
                valor = valor.get(chave) if isinstance(valor, dict) else None
            if valor not in (None, "", "null"):
                return valor
        except AttributeError:
            continue
    return None


def extrair_partes_numero_controle(numero_controle: str):
    """
    Exemplo:
    19875046000182-1-000165/2024
    -> orgao=19875046000182, sequencial=165, ano=2024
    """
    try:
        parte_orgao, resto = str(numero_controle).split("-1-")
        sequencial, ano = resto.split("/")
        return {
            "orgao": parte_orgao,
            "sequencial": str(int(sequencial)),
            "ano": ano
        }
    except Exception:
        return None


def salvar_licitacao_pncp(item: dict):
    identificador = (
        item.get("numeroControlePNCP")
        or item.get("numeroCompra")
        or item.get("sequencialCompra")
    )

    if not identificador:
        return None

    identificador = str(identificador)

    licitacao = Licitacao.query.filter_by(
        identificador_unico_pncp=identificador
    ).first()

    orgao_licitante = (
        get_nested(
            item,
            ("orgaoEntidade", "razaoSocial"),
            ("unidadeOrgao", "nomeUnidade"),
            ("orgaoEntidade", "nomeFantasia"),
        )
        or None
    )

    modalidade = str(
        item.get("modalidadeNome")
        or item.get("modalidadeId")
        or ""
    )

    objeto = item.get("objetoCompra")
    data_publicacao = parse_data(item.get("dataPublicacaoPncp"))
    data_abertura_propostas = parse_data(item.get("dataAberturaProposta"))

    data_encerramento_proposta = parse_data(
        item.get("dataEncerramentoProposta")
        or item.get("dataEncerramento")
        or item.get("dataFinalProposta")
    )

    localidade_uf = get_nested(
        item,
        ("unidadeOrgao", "ufSigla"),
        ("orgaoEntidade", "ufSigla"),
        ("ufSigla",),
        ("unidadeOrgao", "endereco", "ufSigla"),
        ("orgaoEntidade", "endereco", "ufSigla"),
    )

    localidade_municipio = get_nested(
        item,
        ("unidadeOrgao", "municipioNome"),
        ("orgaoEntidade", "municipioNome"),
        ("municipioNome",),
        ("unidadeOrgao", "endereco", "municipioNome"),
        ("orgaoEntidade", "endereco", "municipioNome"),
    )

    numero_controle = item.get("numeroControlePNCP")

    link_fonte = (
        item.get("linkSistemaOrigem")
        or item.get("linkProcessoEletronico")
        or item.get("linkPortalNacional")
        or item.get("url")
    )

    link_edital = (
        item.get("linkEdital")
        or item.get("arquivoEdital")
        or item.get("urlEdital")
        or item.get("linkArquivo")
    )

    if not link_fonte and numero_controle:
        partes = extrair_partes_numero_controle(numero_controle)
        if partes:
            link_fonte = (
                f"https://pncp.gov.br/app/editais/"
                f"{partes['orgao']}/{partes['ano']}/{partes['sequencial']}"
            )

    if not link_edital and numero_controle:
        link_edital = descobrir_primeiro_pdf_pncp(numero_controle)

    if not link_edital:
        link_edital = None

    texto_integral_aviso = item.get("informacaoComplementar")
    valor_estimado = item.get("valorTotalEstimado")
    situacao = item.get("situacaoCompraNome")
    numero_processo = item.get("numeroProcesso")

    agora = datetime.utcnow()

    if licitacao:
        licitacao.numero_processo = numero_processo or licitacao.numero_processo
        licitacao.orgao_licitante = orgao_licitante or licitacao.orgao_licitante
        licitacao.modalidade = modalidade or licitacao.modalidade
        licitacao.objeto = objeto or licitacao.objeto
        licitacao.data_publicacao = data_publicacao or licitacao.data_publicacao
        licitacao.data_abertura_propostas = (
            data_abertura_propostas or licitacao.data_abertura_propostas
        )
        licitacao.data_encerramento_proposta = (
            data_encerramento_proposta or licitacao.data_encerramento_proposta
        )
        licitacao.localidade_uf = localidade_uf or licitacao.localidade_uf
        licitacao.localidade_municipio = (
            localidade_municipio or licitacao.localidade_municipio
        )
        licitacao.link_fonte = link_fonte or licitacao.link_fonte
        licitacao.link_edital = link_edital or licitacao.link_edital
        licitacao.texto_integral_aviso = (
            texto_integral_aviso or licitacao.texto_integral_aviso
        )
        licitacao.valor_estimado = (
            valor_estimado
            if valor_estimado is not None
            else licitacao.valor_estimado
        )
        licitacao.situacao = situacao or licitacao.situacao

        # Não baixa edital automaticamente
        licitacao.caminho_edital = None

        licitacao.data_ultima_atualizacao = agora

        db.session.flush()
        return licitacao

    licitacao = Licitacao(
        numero_processo=numero_processo,
        identificador_unico_pncp=identificador,
        orgao_licitante=orgao_licitante,
        modalidade=modalidade,
        objeto=objeto,
        data_publicacao=data_publicacao,
        data_abertura_propostas=data_abertura_propostas,
        data_encerramento_proposta=data_encerramento_proposta,
        localidade_uf=localidade_uf,
        localidade_municipio=localidade_municipio,
        fonte_dados="PNCP",
        link_fonte=link_fonte,
        link_edital=link_edital,
        caminho_edital=None,
        texto_integral_aviso=texto_integral_aviso,
        valor_estimado=valor_estimado,
        situacao=situacao,
        data_coleta=agora,
        data_ultima_atualizacao=agora,
    )

    db.session.add(licitacao)
    db.session.flush()
    return licitacao


def vincular_licitacao_cliente(cliente_id: int, licitacao_id: int, termo_encontrado: str):
    existente = LicitacaoCliente.query.filter_by(
        cliente_id=cliente_id,
        licitacao_id=licitacao_id,
        termo_encontrado=termo_encontrado,
    ).first()

    if existente:
        return existente, False

    novo = LicitacaoCliente(
        cliente_id=cliente_id,
        licitacao_id=licitacao_id,
        termo_encontrado=termo_encontrado,
        email_enviado=False,
        alerta_48h_enviado=False,
        alerta_24h_enviado=False,
    )

    try:
        with db.session.begin_nested():
            db.session.add(novo)
            db.session.flush()
        return novo, True

    except IntegrityError:
        existente = LicitacaoCliente.query.filter_by(
            cliente_id=cliente_id,
            licitacao_id=licitacao_id,
            termo_encontrado=termo_encontrado,
        ).first()

        if existente:
            return existente, False

        raise