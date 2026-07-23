"""
Exporta os dados do banco de volta para um arquivo .xlsx legível.

Importante: isso NUNCA sobrescreve `data/raw/Jogos_Zerados_-_Max.xlsx`
(esse arquivo é o registro histórico da v1.0 e fica congelado). A partir
da v4.0, o banco de dados é a fonte da verdade, e este módulo gera um
Excel *derivado* dele (`data/processed/Jogos_Zerados_atualizado.xlsx`)
sempre que um jogo é cadastrado ou editado pelo app — só pra você ter
uma versão em planilha pra consultar/compartilhar se quiser, sem
precisar editar nada manualmente nunca mais.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

CABECALHO = [
    "Nome", "Console", "Gênero", "Tipo", "Data", "Tempo (horas)",
    "Nota", "Dificuldade", "Condição de Zeramento",
    "Capa (RAWG)", "Nota Metacritic",
]


def exportar_para_xlsx(caminho_db: str | Path, caminho_xlsx: str | Path) -> None:
    conn = sqlite3.connect(caminho_db)
    conn.row_factory = sqlite3.Row
    try:
        jogos = conn.execute(
            """
            SELECT j.nome, j.console, j.genero, j.tipo, j.data, j.tempo_horas,
                   j.nota, j.dificuldade, j.condicao_zeramento,
                   e.capa_url, e.nota_metacritic
            FROM jogos_zerados j
            LEFT JOIN enriquecimento_rawg e ON e.jogo_id = j.id
            ORDER BY j.id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Jogos Zerados"
    ws.append(CABECALHO)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for jogo in jogos:
        ws.append(
            [
                jogo["nome"], jogo["console"], jogo["genero"], jogo["tipo"],
                jogo["data"], jogo["tempo_horas"], jogo["nota"],
                jogo["dificuldade"], jogo["condicao_zeramento"],
                jogo["capa_url"], jogo["nota_metacritic"],
            ]
        )

    for coluna in ws.columns:
        maior = max((len(str(c.value)) for c in coluna if c.value is not None), default=10)
        ws.column_dimensions[coluna[0].column_letter].width = min(maior + 2, 60)

    caminho_xlsx = Path(caminho_xlsx)
    caminho_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho_xlsx)
