"""
Testes do módulo de enriquecimento.

Não fazem nenhuma chamada real à API da RAWG — usamos `unittest.mock`
para simular as respostas. Isso é importante: testes que dependem de
internet são lentos, instáveis (podem falhar por fora do nosso controle)
e, no caso de uma API paga por cota, custam requisições à toa.
"""

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.enrichment.enrich import _calcular_confianca, enriquecer_jogos


def test_confianca_alta_quando_nome_bate_exatamente():
    resultado_rawg = {"name": "God of War"}
    assert _calcular_confianca("God of War", resultado_rawg) == "alta"


def test_confianca_alta_ignora_diferenca_de_maiusculas_e_espacos():
    resultado_rawg = {"name": "god of war"}
    assert _calcular_confianca("  God Of War  ", resultado_rawg) == "alta"


def test_confianca_baixa_quando_nomes_diferem():
    resultado_rawg = {"name": "God of War: Ragnarök"}
    assert _calcular_confianca("God of War", resultado_rawg) == "baixa"


def _criar_banco_temporario(tmp_path):
    caminho_db = tmp_path / "teste.db"
    conn = sqlite3.connect(caminho_db)
    conn.execute("CREATE TABLE jogos_zerados (id INTEGER PRIMARY KEY, nome TEXT)")
    conn.execute("INSERT INTO jogos_zerados (id, nome) VALUES (1, 'God of War')")
    conn.execute("INSERT INTO jogos_zerados (id, nome) VALUES (2, 'Jogo Que Não Existe De Verdade')")
    conn.commit()
    conn.close()
    return caminho_db


def test_enriquecer_jogos_com_resultado_encontrado(tmp_path):
    caminho_db = _criar_banco_temporario(tmp_path)

    respostas_simuladas = {
        "God of War": {
            "id": 4200,
            "name": "God of War",
            "background_image": "https://exemplo.com/capa.jpg",
            "released": "2018-04-20",
            "metacritic": 94,
            "genres": [{"name": "Action"}, {"name": "Adventure"}],
        },
        "Jogo Que Não Existe De Verdade": None,
    }

    with patch("src.enrichment.enrich.buscar_jogo", side_effect=lambda nome: respostas_simuladas[nome]):
        resultados = enriquecer_jogos(caminho_db)

    assert len(resultados) == 2
    encontrado = next(r for r in resultados if r.jogo_id == 1)
    nao_encontrado = next(r for r in resultados if r.jogo_id == 2)

    assert encontrado.encontrado is True
    assert encontrado.confianca == "alta"
    assert nao_encontrado.encontrado is False


def test_enriquecer_jogos_e_idempotente(tmp_path):
    """Rodar duas vezes não deve consultar a API de novo pros mesmos jogos."""
    caminho_db = _criar_banco_temporario(tmp_path)

    chamadas = []

    def busca_simulada(nome):
        chamadas.append(nome)
        return {"id": 1, "name": nome, "background_image": None, "released": None, "metacritic": None, "genres": []}

    with patch("src.enrichment.enrich.buscar_jogo", side_effect=busca_simulada):
        enriquecer_jogos(caminho_db)
        enriquecer_jogos(caminho_db)

    # cada jogo só deve ter sido consultado 1 vez, mesmo com 2 execuções
    assert len(chamadas) == 2
