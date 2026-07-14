"""
Ponto de entrada da v3.0: enriquece os jogos já limpos (v2.0) com dados
da RAWG (capa, ano de lançamento, nota Metacritic).

Pré-requisito: já ter rodado `python -m src.run_etl` (v2.0) antes, e ter
um arquivo `.env` na raiz do projeto com a variável RAWG_API_KEY definida
(veja .env.example).

Uso:
    python -m src.run_enrich
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from src.enrichment.enrich import enriquecer_jogos

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "processed" / "jogos_zerados.db"


def main() -> None:
    load_dotenv(RAIZ / ".env")

    if not BANCO.exists():
        print(f"Banco de dados não encontrado em {BANCO}.")
        print("Rode primeiro: python -m src.run_etl")
        return

    print("Consultando a RAWG para cada jogo (isso pode levar alguns segundos)...")
    resultados = enriquecer_jogos(BANCO)

    if not resultados:
        print("Nada a fazer: todos os jogos já foram enriquecidos anteriormente.")
        return

    encontrados = [r for r in resultados if r.encontrado]
    nao_encontrados = [r for r in resultados if not r.encontrado and not r.erro]
    com_erro = [r for r in resultados if r.erro]
    baixa_confianca = [r for r in encontrados if r.confianca == "baixa"]

    print(f"\n{len(resultados)} jogo(s) processado(s) nesta execução:")
    print(f"  encontrados na RAWG:      {len(encontrados)}")
    print(f"  não encontrados:          {len(nao_encontrados)}")
    print(f"  erro de comunicação:      {len(com_erro)}")

    if baixa_confianca:
        print(f"\n{len(baixa_confianca)} jogo(s) encontrados com confiança BAIXA (vale conferir manualmente):")
        for r in baixa_confianca:
            print(f"  - {r.nome_original}")

    if nao_encontrados:
        print(f"\n{len(nao_encontrados)} jogo(s) não encontrados na RAWG:")
        for r in nao_encontrados:
            print(f"  - {r.nome_original}")

    if com_erro:
        print(f"\n{len(com_erro)} jogo(s) com erro de comunicação (tente rodar de novo):")
        for r in com_erro:
            print(f"  - {r.nome_original}: {r.erro}")


if __name__ == "__main__":
    main()
