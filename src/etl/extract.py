"""
Extração dos dados brutos da planilha "Jogos Zerados".

A aba principal ("Jogos Zerados") tem, além da tabela de jogos (colunas A a J),
outras mini-tabelas soltas nas colunas mais à direita (ranking de notas,
desafios, etc). Este módulo lê SOMENTE a tabela de jogos, sem tentar
interpretar ou corrigir nada — a limpeza fica isolada em `clean.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openpyxl

# Mapeamento explícito das colunas usadas na aba "Jogos Zerados".
# Se a estrutura da planilha mudar, é só ajustar aqui.
COLUNAS = {
    "ordem": 1,
    "nome": 2,
    "console": 3,
    "genero": 4,
    "tipo": 5,
    "data": 6,
    "tempo": 7,
    "nota": 8,
    "dificuldade": 9,
    "condicao_zeramento": 10,
}

ABA_PRINCIPAL = "Jogos Zerados"
LINHA_INICIAL = 2  # linha 1 é cabeçalho


@dataclass
class JogoBruto:
    """Representa uma linha da planilha, sem nenhum tratamento."""

    linha_planilha: int
    ordem: Any
    nome: Any
    console: Any
    genero: Any
    tipo: Any
    data: Any
    tempo: Any
    nota: Any
    dificuldade: Any
    condicao_zeramento: Any


def extrair_jogos(caminho_planilha: str | Path) -> list[JogoBruto]:
    """Lê a aba 'Jogos Zerados' e retorna uma lista de registros brutos.

    Para de ler quando encontra 3 linhas seguidas sem nome de jogo —
    isso evita varrer as ~50 mil linhas vazias que a planilha reserva
    por causa da fórmula de contagem automática na coluna A.
    """
    wb = openpyxl.load_workbook(caminho_planilha, data_only=True)
    ws = wb[ABA_PRINCIPAL]

    registros: list[JogoBruto] = []
    linhas_vazias_seguidas = 0
    linha = LINHA_INICIAL

    while linhas_vazias_seguidas < 3:
        valores = {
            campo: ws.cell(row=linha, column=col).value
            for campo, col in COLUNAS.items()
        }

        if valores["nome"] is None:
            linhas_vazias_seguidas += 1
            linha += 1
            continue

        linhas_vazias_seguidas = 0
        registros.append(JogoBruto(linha_planilha=linha, **valores))
        linha += 1

    return registros
