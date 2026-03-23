import requests

def consultar_cnpj_basica(cnpj_digits: str):
    """
    Consulta gratuita via BrasilAPI.
    Retorna:
      { ok: True, data: {...} }
      ou
      { ok: False, error: "...", status: ..., detail?: "..." }
    """
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"

    try:
        resp = requests.get(
            url,
            timeout=12,
            headers={"User-Agent": "buscador-licitacoes/1.0"}
        )

        if resp.status_code == 404:
            return {"ok": False, "error": "CNPJ não encontrado.", "status": 404}

        if resp.status_code == 429:
            return {
                "ok": False,
                "error": "Muitas consultas ao serviço de CNPJ. Tente novamente em alguns minutos.",
                "status": 429
            }

        if resp.status_code != 200:
            body = (resp.text or "")[:300]
            return {
                "ok": False,
                "error": "Falha ao consultar o serviço de CNPJ.",
                "status": resp.status_code,
                "detail": body
            }

        data = resp.json() or {}

        return {
            "ok": True,
            "status": 200,
            "data": {
                "razao_social": data.get("razao_social") or "",
                "nome_fantasia": data.get("nome_fantasia") or "",
                "uf": data.get("uf") or "",
                "municipio": data.get("municipio") or "",
                "situacao": data.get("descricao_situacao_cadastral") or "",
            }
        }

    except requests.Timeout:
        return {"ok": False, "error": "Timeout ao consultar o serviço de CNPJ.", "status": "timeout"}

    except requests.RequestException as e:
        return {
            "ok": False,
            "error": "Falha de conexão ao consultar o serviço de CNPJ.",
            "status": "network",
            "detail": str(e)
        }

    except Exception as e:
        return {
            "ok": False,
            "error": "Erro inesperado ao consultar o serviço de CNPJ.",
            "status": "unexpected",
            "detail": str(e)
        }