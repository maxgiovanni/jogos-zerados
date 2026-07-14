"""
Cliente HTTP para a API da RAWG (https://rawg.io/apidocs).

Isolar as chamadas de rede num módulo separado facilita testar o resto
do código sem depender de internet, e deixa claro qual é o único lugar
do projeto que efetivamente "sai" pra fora.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

BASE_URL = "https://api.rawg.io/api"
TIMEOUT_SEGUNDOS = 10
PAUSA_ENTRE_REQUISICOES = 0.5  # educado com a cota gratuita da API


class RawgApiError(Exception):
    """Erro genérico de comunicação com a API da RAWG."""


def _obter_chave_api() -> str:
    chave = os.getenv("RAWG_API_KEY")
    if not chave or chave == "coloque_sua_chave_aqui":
        raise RawgApiError(
            "RAWG_API_KEY não configurada. Copie .env.example para .env "
            "e preencha com sua chave (veja README, seção v3.0)."
        )
    return chave


def buscar_jogo(nome: str) -> dict[str, Any] | None:
    """Busca um jogo pelo nome e retorna o resultado mais relevante (ou None).

    A RAWG já ordena os resultados por relevância, então usamos o primeiro
    item da lista. Retorna None se a busca não encontrar nada.
    """
    chave = _obter_chave_api()

    resposta = requests.get(
        f"{BASE_URL}/games",
        params={"key": chave, "search": nome, "page_size": 1},
        timeout=TIMEOUT_SEGUNDOS,
    )
    time.sleep(PAUSA_ENTRE_REQUISICOES)

    if resposta.status_code != 200:
        raise RawgApiError(
            f"RAWG retornou status {resposta.status_code} ao buscar '{nome}': {resposta.text[:200]}"
        )

    resultados = resposta.json().get("results", [])
    return resultados[0] if resultados else None
