"""
Enriquecimento dos jogos já tratados (v2.0) com dados externos da RAWG:
capa, ano de lançamento e nota do Metacritic.

Idempotente por design: jogos que já foram enriquecidos numa execução
anterior não são consultados de novo na API (evita gastar cota gratuita
à toa). Jogos não encontrados na RAWG também ficam registrados, com
'encontrado = 0', pra não ficar tentando de novo a cada execução —
se quiser forçar uma nova tentativa, é só apagar a linha correspondente
na tabela `enriquecimento_rawg`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .rawg_client import RawgApiError, buscar_jogo

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS enriquecimento_rawg (
    jogo_id INTEGER PRIMARY KEY REFERENCES jogos_zerados(id),
    rawg_id INTEGER,
    nome_rawg TEXT,
    capa_url TEXT,
    data_lancamento TEXT,
    nota_metacritic REAL,
    generos_rawg TEXT,
    encontrado INTEGER NOT NULL,
    confianca_match TEXT
);
"""


@dataclass
class ResultadoEnriquecimento:
    jogo_id: int
    nome_original: str
    encontrado: bool
    confianca: str | None = None
    erro: str | None = None


def _ja_enriquecidos(conn: sqlite3.Connection) -> set[int]:
    cursor = conn.execute("SELECT jogo_id FROM enriquecimento_rawg")
    return {row[0] for row in cursor.fetchall()}


def _calcular_confianca(nome_original: str, resultado_rawg: dict) -> str:
    """Marca 'alta' quando o nome bate quase exatamente com o resultado
    da RAWG, e 'baixa' quando é só o resultado mais relevante da busca —
    isso ajuda a revisar manualmente casos ambíguos depois (ex: remakes,
    coletâneas, jogos com nomes muito genéricos)."""
    nome_normalizado = nome_original.strip().lower()
    nome_rawg_normalizado = str(resultado_rawg.get("name", "")).strip().lower()
    return "alta" if nome_normalizado == nome_rawg_normalizado else "baixa"


def enriquecer_jogos(caminho_db: str | Path) -> list[ResultadoEnriquecimento]:
    conn = sqlite3.connect(caminho_db)
    conn.execute(CREATE_TABLE_SQL)

    ja_feitos = _ja_enriquecidos(conn)
    jogos = conn.execute("SELECT id, nome FROM jogos_zerados").fetchall()

    resultados: list[ResultadoEnriquecimento] = []

    for jogo_id, nome in jogos:
        if jogo_id in ja_feitos:
            continue

        try:
            achado = buscar_jogo(nome)
        except RawgApiError as e:
            resultados.append(ResultadoEnriquecimento(jogo_id, nome, encontrado=False, erro=str(e)))
            continue

        if achado is None:
            conn.execute(
                "INSERT INTO enriquecimento_rawg (jogo_id, encontrado) VALUES (?, 0)",
                (jogo_id,),
            )
            resultados.append(ResultadoEnriquecimento(jogo_id, nome, encontrado=False))
            continue

        confianca = _calcular_confianca(nome, achado)
        conn.execute(
            """
            INSERT INTO enriquecimento_rawg
                (jogo_id, rawg_id, nome_rawg, capa_url, data_lancamento,
                 nota_metacritic, generos_rawg, encontrado, confianca_match)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                jogo_id,
                achado.get("id"),
                achado.get("name"),
                achado.get("background_image"),
                achado.get("released"),
                achado.get("metacritic"),
                ", ".join(g["name"] for g in achado.get("genres", [])),
                confianca,
            ),
        )
        resultados.append(ResultadoEnriquecimento(jogo_id, nome, encontrado=True, confianca=confianca))

    conn.commit()
    conn.close()
    return resultados
