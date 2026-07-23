"""Carga dos dados já limpos: gera um banco SQLite e um CSV em data/processed."""

from __future__ import annotations

import csv
import datetime
import sqlite3
from pathlib import Path

from .clean import DesafioLimpo, JogoDropadoLimpo, JogoLimpo

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
    condicao_zeramento TEXT,
    comentario_pessoal TEXT
);
"""

CREATE_TABLE_DROPADOS_SQL = """
CREATE TABLE IF NOT EXISTS jogos_dropados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linha_planilha INTEGER,
    nome TEXT NOT NULL,
    console TEXT,
    nota REAL
);
"""

CREATE_TABLE_DESAFIOS_SQL = """
CREATE TABLE IF NOT EXISTS desafios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ano INTEGER NOT NULL,
    progresso REAL,
    descricao TEXT NOT NULL
);
"""

CAMPOS_CSV = [
    "linha_planilha", "ordem", "nome", "console", "genero", "tipo", "data",
    "tempo_horas", "tempo_status", "tempo_bruto", "nota", "dificuldade",
    "condicao_zeramento", "comentario_pessoal",
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


def migrar_esquema(conn: sqlite3.Connection) -> None:
    """Adiciona colunas novas em bancos criados por uma versão anterior
    do projeto, sem apagar nada. Sempre que uma coluna nova for
    adicionada ao esquema, um ALTER TABLE 'silencioso' (ignora erro se
    a coluna já existir) entra aqui."""
    try:
        conn.execute("ALTER TABLE jogos_zerados ADD COLUMN comentario_pessoal TEXT")
    except sqlite3.OperationalError:
        pass  # coluna já existe


def salvar_sqlite(jogos: list[JogoLimpo], caminho_db: str | Path) -> None:
    """Salva os jogos no SQLite fazendo 'upsert' (atualiza se já existe,
    insere se é novo) em vez de apagar e recriar a tabela inteira.

    Isso é essencial porque a planilha é atualizada manualmente ao longo
    do tempo (você continua zerando jogos!). Se a cada execução a gente
    recriasse a tabela do zero, os IDs internos dos jogos mudariam, e
    isso quebraria o vínculo com a tabela de enriquecimento da RAWG
    (v3.0) — teríamos que buscar tudo de novo na API a cada atualização,
    gastando cota à toa.

    A identidade de um jogo aqui é o par (nome, console): é a combinação
    mais estável que temos, já que a posição da linha na planilha muda
    quando você insere jogos novos no topo.
    """
    caminho_db = Path(caminho_db)
    caminho_db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(caminho_db)
    try:
        conn.execute(CREATE_TABLE_SQL)
        migrar_esquema(conn)

        campos_atualizaveis = [c for c in CAMPOS_CSV if c not in ("nome", "console")]

        for jogo in jogos:
            valores = {
                campo: _formatar_data(getattr(jogo, campo)) if campo == "data" else getattr(jogo, campo)
                for campo in CAMPOS_CSV
            }

            existente = conn.execute(
                "SELECT id FROM jogos_zerados WHERE nome = ? AND console = ?",
                (valores["nome"], valores["console"]),
            ).fetchone()

            if existente:
                jogo_id = existente[0]
                set_clause = ", ".join(f"{campo} = ?" for campo in campos_atualizaveis)
                conn.execute(
                    f"UPDATE jogos_zerados SET {set_clause} WHERE id = ?",
                    (*(valores[campo] for campo in campos_atualizaveis), jogo_id),
                )
            else:
                conn.execute(
                    f"""
                    INSERT INTO jogos_zerados ({', '.join(CAMPOS_CSV)})
                    VALUES ({', '.join('?' for _ in CAMPOS_CSV)})
                    """,
                    tuple(valores[campo] for campo in CAMPOS_CSV),
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


def salvar_dropados(jogos: list[JogoDropadoLimpo], caminho_db: str | Path) -> None:
    """Mesma lógica de upsert por (nome, console) usada nos jogos zerados."""
    conn = sqlite3.connect(caminho_db)
    try:
        conn.execute(CREATE_TABLE_DROPADOS_SQL)
        for jogo in jogos:
            existente = conn.execute(
                "SELECT id FROM jogos_dropados WHERE nome = ? AND console = ?",
                (jogo.nome, jogo.console),
            ).fetchone()
            if existente:
                conn.execute(
                    "UPDATE jogos_dropados SET linha_planilha = ?, nota = ? WHERE id = ?",
                    (jogo.linha_planilha, jogo.nota, existente[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO jogos_dropados (linha_planilha, nome, console, nota) VALUES (?, ?, ?, ?)",
                    (jogo.linha_planilha, jogo.nome, jogo.console, jogo.nota),
                )
        conn.commit()
    finally:
        conn.close()


def salvar_desafios(desafios: list[DesafioLimpo], caminho_db: str | Path) -> None:
    """Desafios são substituídos por completo a cada execução (upsert por
    ano + descrição): diferente dos jogos, aqui não há um vínculo externo
    (como o enriquecimento da RAWG) que dependa do ID permanecer estável."""
    conn = sqlite3.connect(caminho_db)
    try:
        conn.execute(CREATE_TABLE_DESAFIOS_SQL)
        for desafio in desafios:
            existente = conn.execute(
                "SELECT id FROM desafios WHERE ano = ? AND descricao = ?",
                (desafio.ano, desafio.descricao),
            ).fetchone()
            if existente:
                conn.execute(
                    "UPDATE desafios SET progresso = ? WHERE id = ?",
                    (desafio.progresso, existente[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO desafios (ano, progresso, descricao) VALUES (?, ?, ?)",
                    (desafio.ano, desafio.progresso, desafio.descricao),
                )
        conn.commit()
    finally:
        conn.close()
