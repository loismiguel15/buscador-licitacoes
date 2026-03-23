import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

EFI_CLIENT_ID = os.getenv("EFI_CLIENT_ID")
EFI_CLIENT_SECRET = os.getenv("EFI_CLIENT_SECRET")
EFI_BASE_URL = os.getenv("EFI_BASE_URL")


def get_efi_token():
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
    response.raise_for_status()

    return response.json()

def criar_link_pagamento(nome_plano, valor):
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
            "email": "teste@teste.com"
        },
        "settings": {
            "payment_method": "all",
            "expire_at": "2026-12-31",
            "request_delivery_address": False
        }
    }

    response = requests.post(url, json=body, headers=headers, timeout=30)

    print("Status:", response.status_code)
    print("Resposta:", response.text)

    response.raise_for_status()
    return response.json()