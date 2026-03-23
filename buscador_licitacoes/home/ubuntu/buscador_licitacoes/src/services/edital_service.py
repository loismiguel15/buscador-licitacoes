import re
import requests
from io import BytesIO


def _nome_seguro_arquivo(nome: str) -> str:
    nome = re.sub(r"[^\w\-\.]+", "_", str(nome))
    return nome[:150]


def baixar_edital_em_memoria(url: str, identificador: str):
    if not url:
        return None, None

    try:
        response = requests.get(
            url,
            timeout=40,
            allow_redirects=True,
            headers={
                "User-Agent": "Buscador-Licitacoes/1.0",
                "Accept": "application/pdf,application/octet-stream,*/*",
            },
        )

        if not response.ok:
            print(f"Erro ao baixar edital | status={response.status_code} | url={url}")
            return None, None

        content_type = (response.headers.get("Content-Type") or "").lower()
        content_disposition = (response.headers.get("Content-Disposition") or "").lower()
        tamanho = len(response.content or b"")

        eh_arquivo_valido = (
            "application/pdf" in content_type
            or "application/octet-stream" in content_type
            or ".pdf" in content_disposition
            or url.lower().endswith(".pdf")
        ) and tamanho > 1000

        if not eh_arquivo_valido:
            print(
                f"Arquivo não parece válido | content_type={content_type} | "
                f"url={response.url} | tamanho={tamanho}"
            )
            return None, None

        nome_base = _nome_seguro_arquivo(identificador or "edital")
        nome_arquivo = f"{nome_base}.pdf"

        arquivo = BytesIO(response.content)
        arquivo.seek(0)

        return arquivo, nome_arquivo

    except Exception as e:
        print(f"Erro ao baixar edital | url={url} | erro={e}")
        return None, None