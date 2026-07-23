"""
Repositório de dados: camada única de acesso ao SQLite, usada pelo
dashboard (Streamlit). Mantém todo o SQL num só lugar, separado da
lógica de interface — assim o app não precisa saber nada sobre tabelas
ou colunas, só chama essas funções.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.etl.load import (
    CAMPOS_CSV,
    CREATE_TABLE_DESAFIOS_SQL,
    CREATE_TABLE_DROPADOS_SQL,
    CREATE_TABLE_SQL,
)
from src.enrichment.enrich import CREATE_TABLE_SQL as CREATE_TABLE_ENRIQUECIMENTO_SQL

CAMPOS_FORMULARIO = [c for c in CAMPOS_CSV if c not in ("linha_planilha", "ordem")]


def _connect(caminho_db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(caminho_db)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_TABLE_SQL)
    conn.execute(CREATE_TABLE_ENRIQUECIMENTO_SQL)
    conn.execute(CREATE_TABLE_DROPADOS_SQL)
    conn.execute(CREATE_TABLE_DESAFIOS_SQL)
    return conn


_SELECT_JOGO_COM_RAWG = """
    SELECT j.*, e.capa_url, e.data_lancamento AS rawg_lancamento,
           e.nota_metacritic, e.generos_rawg, e.encontrado AS rawg_encontrado
    FROM jogos_zerados j
    LEFT JOIN enriquecimento_rawg e ON e.jogo_id = j.id
"""


def listar_jogos(caminho_db: str | Path) -> list[dict[str, Any]]:
    conn = _connect(caminho_db)
    try:
        linhas = conn.execute(f"{_SELECT_JOGO_COM_RAWG} ORDER BY j.id DESC").fetchall()
        return [dict(linha) for linha in linhas]
    finally:
        conn.close()


def obter_jogo(caminho_db: str | Path, jogo_id: int) -> dict[str, Any] | None:
    conn = _connect(caminho_db)
    try:
        linha = conn.execute(f"{_SELECT_JOGO_COM_RAWG} WHERE j.id = ?", (jogo_id,)).fetchone()
        return dict(linha) if linha else None
    finally:
        conn.close()


def inserir_jogo(caminho_db: str | Path, dados: dict[str, Any]) -> int:
    """Insere um jogo cadastrado manualmente pelo app (não veio da
    planilha, então 'linha_planilha' e 'ordem' ficam nulos)."""
    conn = _connect(caminho_db)
    try:
        campos = ["linha_planilha", "ordem"] + CAMPOS_FORMULARIO
        valores = [None, None] + [dados.get(campo) for campo in CAMPOS_FORMULARIO]
        cursor = conn.execute(
            f"INSERT INTO jogos_zerados ({', '.join(campos)}) VALUES ({', '.join('?' for _ in campos)})",
            valores,
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def atualizar_jogo(caminho_db: str | Path, jogo_id: int, dados: dict[str, Any]) -> None:
    conn = _connect(caminho_db)
    try:
        campos = [c for c in CAMPOS_FORMULARIO if c in dados]
        set_clause = ", ".join(f"{campo} = ?" for campo in campos)
        conn.execute(
            f"UPDATE jogos_zerados SET {set_clause} WHERE id = ?",
            [dados[campo] for campo in campos] + [jogo_id],
        )
        conn.commit()
    finally:
        conn.close()


def listar_dropados(caminho_db: str | Path) -> list[dict[str, Any]]:
    conn = _connect(caminho_db)
    try:
        linhas = conn.execute("SELECT * FROM jogos_dropados ORDER BY nome").fetchall()
        return [dict(linha) for linha in linhas]
    finally:
        conn.close()


def listar_desafios(caminho_db: str | Path) -> list[dict[str, Any]]:
    conn = _connect(caminho_db)
    try:
        linhas = conn.execute("SELECT * FROM desafios ORDER BY ano DESC, id").fetchall()
        return [dict(linha) for linha in linhas]
    finally:
        conn.close()
