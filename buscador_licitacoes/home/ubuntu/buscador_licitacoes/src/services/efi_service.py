import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

EFI_CLIENT_ID = os.getenv("EFI_CLIENT_ID")
EFI_CLIENT_SECRET = os.getenv("EFI_CLIENT_SECRET")
EFI_BASE_URL = os.getenv("EFI_BASE_URL")


def validar_config_efi():
    if not EFI_CLIENT_ID:
        raise Exception("EFI_CLIENT_ID não configurado.")
    if not EFI_CLIENT_SECRET:
        raise Exception("EFI_CLIENT_SECRET não configurado.")
    if not EFI_BASE_URL:
        raise Exception("EFI_BASE_URL não configurado.")


def get_efi_token():
    validar_config_efi()

    credentials = f"{EFI_CLIENT_ID}:{EFI_CLIENT_SECRET}"
    basic_token = base64.b64encode(credentials.encode()).decode()

    url = f"{EFI_BASE_URL}/v1/authorize"

    headers = {
        "Authorization": f"Basic {basic_token}",
        "Content-Type": "application/json"
    }

    body = {
        "grant_type": "client_credentials"
    }

    response = requests.post(url, json=body, headers=headers, timeout=30)

    print("EFI TOKEN STATUS:", response.status_code)
    print("EFI TOKEN RESPONSE:", response.text)

    response.raise_for_status()

    data = response.json()

    if "access_token" not in data:
        raise Exception(f"Token EFI não retornado corretamente: {data}")

    return data


def criar_link_pagamento(nome_plano, valor, email_cliente):
    token_data = get_efi_token()
    access_token = token_data["access_token"]

    url = f"{EFI_BASE_URL}/v1/charge/one-step/link"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "items": [
            {
                "name": nome_plano,
                "value": int(valor * 100),
                "amount": 1
            }
        ],
        "metadata": {
            "custom_id": "plano_monitoramento_01"
        },
        "customer": {
            "email": email_cliente
        },
        "settings": {
            "payment_method": "all",
            "expire_at": "2026-12-31",
            "request_delivery_address": False
        }
    }

    response = requests.post(url, json=body, headers=headers, timeout=30)

    print("EFI LINK STATUS:", response.status_code)
    print("EFI LINK RESPONSE:", response.text)

    response.raise_for_status()

    data = response.json()

    if "data" not in data:
        raise Exception(f"Resposta inesperada da EFI: {data}")

    return data