from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import unicodedata
from rapidfuzz import fuzz

from src.models import (
    db,
    Cliente,
    ClientePreferencias,
    Licitacao,
    LicitacaoCliente,
    EmailLog,
    MonitoramentoExecucao,
    HistoricoBusca,
)
from src.services.pncp_client import fetch_contratacoes_publicacao
from src.services.licitacao_service import (
    salvar_licitacao_pncp,
    vincular_licitacao_cliente,
)
from src.services.email_service import enviar_email, montar_email_licitacoes


# =========================================
# CONFIG (OTIMIZADO)
# =========================================

MAX_ITENS_EMAIL = 5
TZ_BRASIL = ZoneInfo("America/Sao_Paulo")

# paginação do PNCP
TAMANHO_PAGINA_PNCP = 20
MAX_PAGINAS_PNCP = 3

# limita processamento por execução
MAX_CLIENTES_POR_EXECUCAO = 5
MAX_UFS_POR_CLIENTE = 3
MAX_KEYWORDS_POR_CLIENTE = 5
MAX_LICITACOES_NOVAS_POR_CLIENTE = 30
MAX_ITENS_PROCESSADOS_POR_CLIENTE = 100

# modalidades mais úteis por padrão
MODALIDADES_PADRAO = [4, 6, 8, 9]


# =========================================
# HELPERS
# =========================================

def _agora_brasil():
    return datetime.now(TZ_BRASIL)


def _agora_brasil_naive():
    return _agora_brasil().replace(tzinfo=None)


def _hoje_str():
    return _agora_brasil().strftime("%Y%m%d")


def _ontem_str():
    return (_agora_brasil() - timedelta(days=1)).strftime("%Y%m%d")


def _quebrar_lista_texto(valor: str):
    if not valor:
        return []

    itens = []
    for parte in str(valor).replace(";", ",").split(","):
        texto = parte.strip()
        if texto:
            itens.append(texto)
    return itens


def _parse_modalidade(valor: str):
    try:
        return int(str(valor).strip())
    except Exception:
        return None


def _parse_data_generica(data_str):
    if not data_str:
        return None

    formatos = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
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


def _parse_data_publicacao_item(item: dict):
    return _parse_data_generica(item.get("dataPublicacaoPncp"))


def _obter_registro_execucao():
    registro = MonitoramentoExecucao.query.first()

    if not registro:
        registro = MonitoramentoExecucao(ultima_execucao=None)
        db.session.add(registro)
        db.session.flush()

    return registro


def _remover_acentos(texto: str):
    if not texto:
        return ""

    return "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    ).lower()


def _texto_parecido(texto: str, termo: str, limite=88):
    if not texto or not termo:
        return False

    texto = _remover_acentos(texto)
    termo = _remover_acentos(termo)

    score1 = fuzz.partial_ratio(texto, termo)
    score2 = fuzz.token_sort_ratio(texto, termo)

    return max(score1, score2) >= limite


def _item_combina_com_termo(item: dict, termo: str):
    if not termo:
        return True

    termo_normalizado = _remover_acentos(termo)

    campos = [
        item.get("objetoCompra"),
        item.get("informacaoComplementar"),
        item.get("numeroProcesso"),
        item.get("modalidadeNome"),
    ]

    orgao = item.get("orgaoEntidade") or {}
    unidade = item.get("unidadeOrgao") or {}

    campos.extend([
        orgao.get("razaoSocial"),
        unidade.get("nomeUnidade"),
        orgao.get("nomeFantasia"),
    ])

    textos_normalizados = [
        _remover_acentos(campo)
        for campo in campos
        if campo
    ]

    for texto in textos_normalizados:
        if termo_normalizado in texto:
            return True

    for texto in textos_normalizados:
        if _texto_parecido(texto, termo_normalizado):
            return True

    return False


def _termos_que_combinam_com_item(item: dict, termos: list[str]):
    termos_encontrados = []

    for termo in termos:
        if _item_combina_com_termo(item, termo):
            termos_encontrados.append(termo)

    return termos_encontrados


# =========================================
# HISTÓRICO DE BUSCAS
# =========================================

def _registrar_historico_busca(
    cliente: Cliente,
    keywords,
    ufs,
    modalidades,
    data_inicial,
    data_final,
    total_paginas_consultadas,
    total_itens_recebidos,
    total_licitacoes_novas,
    status="ok",
    erro=None,
):
    try:
        historico = HistoricoBusca(
            cliente_id=cliente.id,
            keywords=", ".join(keywords) if keywords else None,
            ufs=", ".join([uf for uf in ufs if uf]) if ufs else None,
            modalidades=", ".join([str(m) for m in modalidades]) if modalidades else None,
            data_inicial=data_inicial,
            data_final=data_final,
            pagina_inicial=1,
            total_paginas_consultadas=total_paginas_consultadas,
            total_itens_recebidos=total_itens_recebidos,
            total_licitacoes_novas=total_licitacoes_novas,
            executado_em=_agora_brasil_naive(),
            status=status,
            erro=erro,
        )
        db.session.add(historico)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao registrar histórico de busca do cliente {cliente.id}: {e}")


# =========================================
# BUSCA DE LICITAÇÕES POR CLIENTE
# =========================================

def buscar_licitacoes_para_cliente(cliente: Cliente, ultima_execucao: datetime | None):
    preferencias = ClientePreferencias.query.filter_by(
        cliente_id=cliente.id,
        ativo=True,
    ).first()

    if not preferencias:
        return []

    keywords = _quebrar_lista_texto(preferencias.keywords)
    ufs = _quebrar_lista_texto(preferencias.ufs)
    modalidades = _quebrar_lista_texto(preferencias.modalidades)

    if not keywords:
        return []

    keywords = list(dict.fromkeys(
        termo.strip() for termo in keywords if termo and termo.strip()
    ))
    keywords = keywords[:MAX_KEYWORDS_POR_CLIENTE]

    if not ufs:
        ufs = [None]
    else:
        ufs = ufs[:MAX_UFS_POR_CLIENTE]

    if not modalidades:
        modalidades = MODALIDADES_PADRAO

    novas_licitacoes = []
    licitacoes_ids_adicionadas = set()

    data_inicial = _ontem_str()
    data_final = _hoje_str()

    total_paginas_consultadas = 0
    total_itens_recebidos = 0
    erro_busca = None
    contador_itens = 0

    for uf in ufs:
        for modalidade in modalidades:
            codigo_modalidade = _parse_modalidade(modalidade)

            if codigo_modalidade is None:
                print(
                    f"Modalidade inválida ignorada | cliente={cliente.id} | modalidade={modalidade}"
                )
                continue

            for pagina in range(1, MAX_PAGINAS_PNCP + 1):
                try:
                    resposta = fetch_contratacoes_publicacao(
                        data_inicial=data_inicial,
                        data_final=data_final,
                        codigo_modalidade=codigo_modalidade,
                        pagina=pagina,
                        tamanho=TAMANHO_PAGINA_PNCP,
                        uf=uf,
                    )
                    total_paginas_consultadas += 1
                except Exception as e:
                    erro_busca = str(e)
                    print(
                        f"Erro ao consultar PNCP | cliente={cliente.id} | uf={uf} | modalidade={modalidade} | pagina={pagina} | erro={e}"
                    )
                    break

                itens = resposta.get("data", []) or []
                total_itens_recebidos += len(itens)

                if not itens:
                    break

                encontrou_item_novo_na_pagina = False

                for item in itens:
                    contador_itens += 1
                    if contador_itens > MAX_ITENS_PROCESSADOS_POR_CLIENTE:
                        break

                    termos_encontrados = _termos_que_combinam_com_item(item, keywords)

                    if not termos_encontrados:
                        continue

                    data_publicacao_item = _parse_data_publicacao_item(item)

                    if ultima_execucao and data_publicacao_item:
                        if data_publicacao_item <= ultima_execucao:
                            continue

                    encontrou_item_novo_na_pagina = True

                    licitacao = salvar_licitacao_pncp(item)
                    if not licitacao:
                        continue

                    adicionou_essa_licitacao = False

                    for termo in termos_encontrados:
                        _, criado = vincular_licitacao_cliente(
                            cliente_id=cliente.id,
                            licitacao_id=licitacao.id,
                            termo_encontrado=termo,
                        )

                        if criado:
                            adicionou_essa_licitacao = True

                    if adicionou_essa_licitacao and licitacao.id not in licitacoes_ids_adicionadas:
                        novas_licitacoes.append(licitacao)
                        licitacoes_ids_adicionadas.add(licitacao.id)

                    if len(novas_licitacoes) >= MAX_LICITACOES_NOVAS_POR_CLIENTE:
                        break

                if contador_itens > MAX_ITENS_PROCESSADOS_POR_CLIENTE:
                    break

                if len(novas_licitacoes) >= MAX_LICITACOES_NOVAS_POR_CLIENTE:
                    break

                if len(itens) < TAMANHO_PAGINA_PNCP:
                    break

                if ultima_execucao and not encontrou_item_novo_na_pagina:
                    break

            if contador_itens > MAX_ITENS_PROCESSADOS_POR_CLIENTE:
                break

            if len(novas_licitacoes) >= MAX_LICITACOES_NOVAS_POR_CLIENTE:
                break

        if contador_itens > MAX_ITENS_PROCESSADOS_POR_CLIENTE:
            break

        if len(novas_licitacoes) >= MAX_LICITACOES_NOVAS_POR_CLIENTE:
            break

    _registrar_historico_busca(
        cliente=cliente,
        keywords=keywords,
        ufs=ufs,
        modalidades=modalidades,
        data_inicial=data_inicial,
        data_final=data_final,
        total_paginas_consultadas=total_paginas_consultadas,
        total_itens_recebidos=total_itens_recebidos,
        total_licitacoes_novas=len(novas_licitacoes),
        status="erro" if erro_busca else "ok",
        erro=erro_busca,
    )

    return novas_licitacoes


# =========================================
# ENVIO DE ALERTA POR EMAIL
# =========================================

def enviar_alerta_cliente(cliente: Cliente, licitacoes):
    if not licitacoes:
        return 0

    total_encontrado = len(licitacoes)
    licitacoes_email = licitacoes[:MAX_ITENS_EMAIL]

    assunto = f"Novas licitações encontradas para {cliente.nome_empresa}"

    html, texto = montar_email_licitacoes(
        cliente.nome_empresa,
        licitacoes_email,
        total_encontrado=total_encontrado
    )

    try:
        enviar_email(cliente.email_contato, assunto, html, texto)

        ids_licitacoes = [lic.id for lic in licitacoes]

        registros = LicitacaoCliente.query.filter(
            LicitacaoCliente.cliente_id == cliente.id,
            LicitacaoCliente.licitacao_id.in_(ids_licitacoes),
            LicitacaoCliente.email_enviado == False,
        ).all()

        agora = _agora_brasil_naive()

        for registro in registros:
            registro.email_enviado = True
            registro.enviado_em = agora

        log = EmailLog(
            cliente_id=cliente.id,
            destinatario=cliente.email_contato,
            assunto=assunto,
            qtd_resultados=total_encontrado,
            status="ok",
            erro=None,
        )
        db.session.add(log)
        db.session.commit()

        return total_encontrado

    except Exception as e:
        db.session.rollback()

        log = EmailLog(
            cliente_id=cliente.id,
            destinatario=cliente.email_contato,
            assunto=assunto,
            qtd_resultados=total_encontrado,
            status="erro",
            erro=str(e),
        )
        db.session.add(log)
        db.session.commit()

        print(f"Erro ao enviar email para cliente {cliente.id}: {e}")
        return 0


# =========================================
# LEMBRETES DE PRAZO (48H E 24H)
# =========================================

def enviar_lembretes_prazo():
    agora = _agora_brasil_naive()
    limite_48h = agora + timedelta(hours=48)
    limite_24h = agora + timedelta(hours=24)

    total_alertas = 0

    registros = (
        db.session.query(LicitacaoCliente, Cliente, Licitacao)
        .join(Cliente, Cliente.id == LicitacaoCliente.cliente_id)
        .join(Licitacao, Licitacao.id == LicitacaoCliente.licitacao_id)
        .filter(Cliente.ativo == True)
        .all()
    )

    for registro, cliente, licitacao in registros:
        if not licitacao:
            continue

        data_fim = getattr(licitacao, "data_encerramento_proposta", None)
        if not data_fim:
            continue

        objeto_licitacao = licitacao.objeto or "Licitação"

        try:
            if (
                not registro.alerta_48h_enviado
                and agora < data_fim <= limite_48h
                and data_fim > limite_24h
            ):
                assunto = "Lembrete: prazo da licitação termina em até 48h"

                html = f"""
                <p>Olá, {cliente.nome_empresa}.</p>
                <p>A licitação abaixo está próxima do encerramento:</p>
                <p><strong>{objeto_licitacao}</strong></p>
                <p><strong>Prazo final:</strong> {data_fim.strftime('%d/%m/%Y %H:%M')}</p>
                """

                texto = (
                    f"Olá, {cliente.nome_empresa}.\n"
                    f"A licitação '{objeto_licitacao}' está próxima do encerramento.\n"
                    f"Prazo final: {data_fim.strftime('%d/%m/%Y %H:%M')}"
                )

                enviar_email(cliente.email_contato, assunto, html, texto)

                registro.alerta_48h_enviado = True
                registro.alerta_48h_enviado_em = agora
                total_alertas += 1

            elif (
                not registro.alerta_24h_enviado
                and agora < data_fim <= limite_24h
            ):
                assunto = "Lembrete: prazo da licitação termina em até 24h"

                html = f"""
                <p>Olá, {cliente.nome_empresa}.</p>
                <p>A licitação abaixo termina em até 24 horas:</p>
                <p><strong>{objeto_licitacao}</strong></p>
                <p><strong>Prazo final:</strong> {data_fim.strftime('%d/%m/%Y %H:%M')}</p>
                """

                texto = (
                    f"Olá, {cliente.nome_empresa}.\n"
                    f"A licitação '{objeto_licitacao}' termina em até 24 horas.\n"
                    f"Prazo final: {data_fim.strftime('%d/%m/%Y %H:%M')}"
                )

                enviar_email(cliente.email_contato, assunto, html, texto)

                registro.alerta_24h_enviado = True
                registro.alerta_24h_enviado_em = agora
                total_alertas += 1

        except Exception as e:
            print(f"Erro ao enviar lembrete de prazo | cliente={cliente.id} | erro={e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao salvar lembretes de prazo: {e}")

    return total_alertas


# =========================================
# PROCESSO PRINCIPAL
# =========================================

def processar_monitoramento():
    agora = _agora_brasil_naive()
    registro_execucao = _obter_registro_execucao()
    ultima_execucao = registro_execucao.ultima_execucao

    clientes = (
        Cliente.query
        .filter_by(ativo=True)
        .limit(MAX_CLIENTES_POR_EXECUCAO)
        .all()
    )

    total_clientes = 0
    total_novas = 0
    total_emails = 0

    for cliente in clientes:
        total_clientes += 1

        novas_licitacoes = buscar_licitacoes_para_cliente(
            cliente=cliente,
            ultima_execucao=ultima_execucao,
        )

        if novas_licitacoes:
            total_novas += len(novas_licitacoes)
            enviados = enviar_alerta_cliente(cliente, novas_licitacoes)
            total_emails += enviados

    total_lembretes = enviar_lembretes_prazo()

    registro_execucao.ultima_execucao = agora
    db.session.add(registro_execucao)
    db.session.commit()

    return {
        "clientes_processados": total_clientes,
        "novas_licitacoes": total_novas,
        "licitacoes_enviadas_por_email": total_emails,
        "lembretes_enviados": total_lembretes,
        "ultima_execucao_anterior": ultima_execucao.isoformat() if ultima_execucao else None,
        "nova_ultima_execucao": agora.isoformat(),
    }