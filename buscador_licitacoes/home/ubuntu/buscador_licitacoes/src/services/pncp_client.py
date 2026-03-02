import requests

BASE = "https://pncp.gov.br/api/consulta"

def fetch_contratacoes_publicacao(data_inicial: str, data_final: str, codigo_modalidade: int, pagina: int = 1, tamanho: int = 50) -> dict:
    url = f"{BASE}/v1/contratacoes/publicacao"
    params = {
        "dataInicial": data_inicial,             # AAAAMMDD
        "dataFinal": data_final,                 # AAAAMMDD
        "codigoModalidadeContratacao": codigo_modalidade,
        "pagina": pagina,
        "tamanhoPagina": tamanho,                # no manual é opcional
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()