"""Carga dos dados já limpos: gera um banco SQLite e um CSV em data/processed."""

from __future__ import annotations

import csv
import datetime
import sqlite3
from pathlib import Path

from .clean import JogoLimpo

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jogos_zerados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linha_planilha INTEGER,
    ordem INTEGER,
    nome TEXT NOT NULL,
    console TEXT,
    genero TEXT,
    tipo TEXT,
    data TEXT,
    tempo_horas REAL,
    tempo_status TEXT,
    tempo_bruto TEXT,
    nota REAL,
    dificuldade TEXT,
    condicao_zeramento TEXT
);
"""

CAMPOS_CSV = [
    "linha_planilha", "ordem", "nome", "console", "genero", "tipo", "data",
    "tempo_horas", "tempo_status", "tempo_bruto", "nota", "dificuldade",
    "condicao_zeramento",
]


def _formatar_data(valor) -> str | None:
    """A coluna 'data' pode conter datetime.date, datetime.datetime ou até
    string (se a célula original não estava formatada como data). Aqui
    normalizamos tudo para uma string ISO (AAAA-MM-DD) ou deixamos como
    veio, se não for um tipo de data reconhecido."""
    if valor is None:
        return None
    if isinstance(valor, (datetime.date, datetime.datetime)):
        return valor.isoformat()
    return str(valor)


def salvar_sqlite(jogos: list[JogoLimpo], caminho_db: str | Path) -> None:
    caminho_db = Path(caminho_db)
    caminho_db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(caminho_db)
    try:
        conn.execute("DROP TABLE IF EXISTS jogos_zerados")
        conn.execute(CREATE_TABLE_SQL)
        conn.executemany(
            f"""
            INSERT INTO jogos_zerados
                ({', '.join(CAMPOS_CSV)})
            VALUES ({', '.join('?' for _ in CAMPOS_CSV)})
            """,
            [
                tuple(
                    _formatar_data(getattr(jogo, campo)) if campo == "data" else getattr(jogo, campo)
                    for campo in CAMPOS_CSV
                )
                for jogo in jogos
            ],
        )
        conn.commit()
    finally:
        conn.close()


def salvar_csv(jogos: list[JogoLimpo], caminho_csv: str | Path) -> None:
    caminho_csv = Path(caminho_csv)
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)

    with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        for jogo in jogos:
            linha = {campo: getattr(jogo, campo) for campo in CAMPOS_CSV}
            linha["data"] = _formatar_data(linha["data"])
            writer.writerow(linha)
