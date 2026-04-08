import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://pncp.gov.br/api/consulta"
BASE_ARQUIVOS = "https://pncp.gov.br/pncp-api/v1"
CONNECT_TIMEOUT_SECONDS = float(os.getenv("PNCP_CONNECT_TIMEOUT_SECONDS", "5"))
READ_TIMEOUT_SECONDS = float(os.getenv("PNCP_READ_TIMEOUT_SECONDS", "12"))

session = requests.Session()

retry_strategy = Retry(
    total=2,
    connect=2,
    read=2,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
    raise_on_status=False,
)

adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=10,
)

session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update({
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Buscador-Licitacoes/1.0",
})


def _resumo_resposta(response, limite=500):
    content_type = response.headers.get("Content-Type", "")
    corpo = (response.text or "").strip().replace("\n", " ").replace("\r", " ")
    if len(corpo) > limite:
        corpo = corpo[:limite] + "..."
    return (
        f"status={response.status_code} | "
        f"content_type={content_type} | "
        f"url={response.url} | "
        f"body={corpo}"
    )


def fetch_contratacoes_publicacao(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: int,
    pagina: int = 1,
    tamanho: int = 20,
    uf: str | None = None,
) -> dict:
    url = f"{BASE}/v1/contratacoes/publicacao"

    if tamanho > 50:
        tamanho = 50

    if tamanho < 1:
        tamanho = 1

    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "codigoModalidadeContratacao": codigo_modalidade,
        "pagina": pagina,
        "tamanhoPagina": tamanho,
    }

    if uf:
        params["uf"] = uf.strip().upper()

    try:
        response = session.get(
            url,
            params=params,
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
        )
    except requests.exceptions.Timeout:
        raise Exception(
            f"Timeout ao consultar PNCP | url={url} | params={params}"
        )
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro de conexão com PNCP: {e}")

    if response.status_code in (204, 404, 422):
        return {"data": []}

    if not response.ok:
        raise Exception(f"Erro PNCP | {_resumo_resposta(response)}")

    if not response.text or not response.text.strip():
        return {"data": []}

    try:
        data = response.json()
    except ValueError:
        raise Exception(f"Resposta inválida do PNCP | {_resumo_resposta(response)}")

    if isinstance(data, list):
        return {"data": data}

    if not isinstance(data, dict):
        return {"data": []}

    if "data" not in data or data["data"] is None:
        data["data"] = []

    if not isinstance(data["data"], list):
        data["data"] = []

    return data


def extrair_partes_numero_controle(numero_controle: str):
    """
    Exemplo:
    46523049000120-1-000030/2026
    -> orgao=46523049000120, sequencial=30, ano=2026
    """
    if not numero_controle:
        return None

    m = re.match(r"^(\d+)-\d+-(\d+)\/(\d{4})$", str(numero_controle).strip())
    if not m:
        return None

    orgao = m.group(1)
    sequencial = str(int(m.group(2)))
    ano = m.group(3)

    return {
        "orgao": orgao,
        "sequencial": sequencial,
        "ano": ano,
    }


def montar_links_arquivos_pncp(numero_controle: str, max_arquivos: int = 10):
    """
    Monta links candidatos de arquivos públicos do PNCP.
    Não garante que todos existam.
    """
    partes = extrair_partes_numero_controle(numero_controle)
    if not partes:
        return []

    orgao = partes["orgao"]
    sequencial = partes["sequencial"]
    ano = partes["ano"]

    links = []
    for i in range(1, max_arquivos + 1):
        links.append(
            f"{BASE_ARQUIVOS}/orgaos/{orgao}/compras/{ano}/{sequencial}/arquivos/{i}"
        )

    return links


def descobrir_primeiro_pdf_pncp(numero_controle: str, max_arquivos: int = 10):
    """
    Descobre o primeiro arquivo válido do PNCP.
    O PNCP muitas vezes retorna application/octet-stream em vez de application/pdf.
    """
    for url in montar_links_arquivos_pncp(numero_controle, max_arquivos=max_arquivos):
        try:
            response = session.get(
                url,
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                allow_redirects=True
            )
        except requests.exceptions.RequestException:
            continue

        if not response.ok:
            continue

        content_type = (response.headers.get("Content-Type") or "").lower()
        content_disposition = (response.headers.get("Content-Disposition") or "").lower()
        tamanho = len(response.content or b"")

        if "application/pdf" in content_type:
            return url

        if "application/octet-stream" in content_type and tamanho > 1000:
            return url

        if ".pdf" in content_disposition:
            return url

    return None
