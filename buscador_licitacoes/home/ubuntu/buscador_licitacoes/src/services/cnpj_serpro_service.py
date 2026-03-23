import requests

def consultar_cnpj_basica(cnpj_digits: str):
    """
    Consulta grátis via BrasilAPI.
    Retorna:
      { ok: True, data: {...} }
      { ok: False, error: "..." }
    """
    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"
        resp = requests.get(url, timeout=12)

        if resp.status_code == 404:
            return {"ok": False, "error": "CNPJ não encontrado."}

        if resp.status_code != 200:
            return {"ok": False, "error": "Falha ao consultar o serviço de CNPJ."}

        data = resp.json() or {}

        return {
            "ok": True,
            "data": {
                "razao_social": data.get("razao_social"),
                "nome_fantasia": data.get("nome_fantasia"),
                "uf": data.get("uf"),
                "municipio": data.get("municipio"),
                "situacao": data.get("descricao_situacao_cadastral"),
                # compat: nome_empresarial (pra reaproveitar seu código)
                "nome_empresarial": data.get("razao_social"),
            }
        }

    except Exception:
        return {"ok": False, "error": "Falha de conexão ao consultar o serviço de CNPJ."}