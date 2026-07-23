"""
Ponto de entrada do pipeline de ETL da v2.0.

Uso:
    python -m src.run_etl

Lê a planilha original em data/raw/, limpa os dados e gera:
    - data/processed/jogos_zerados.db   (SQLite)
    - data/processed/jogos_zerados.csv  (CSV)

Também imprime um relatório resumido no terminal, listando quantos
registros tiveram algum problema durante a limpeza (nada é descartado
silenciosamente — tudo que não pôde ser interpretado é reportado).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.etl.extract import extrair_jogos, extrair_dropados, extrair_desafios
from src.etl.clean import limpar_jogos, limpar_dropados, limpar_desafios
from src.etl.load import salvar_csv, salvar_sqlite, salvar_dropados, salvar_desafios

RAIZ = Path(__file__).resolve().parent.parent
PLANILHA_ORIGEM = RAIZ / "data" / "raw" / "Jogos_Zerados_-_Max.xlsx"
SAIDA_DB = RAIZ / "data" / "processed" / "jogos_zerados.db"
SAIDA_CSV = RAIZ / "data" / "processed" / "jogos_zerados.csv"


def main() -> None:
    print(f"Lendo planilha: {PLANILHA_ORIGEM}")
    brutos = extrair_jogos(PLANILHA_ORIGEM)
    print(f"  -> {len(brutos)} jogos encontrados")

    limpos, avisos = limpar_jogos(brutos)

    print(f"\nSalvando dados tratados...")
    salvar_sqlite(limpos, SAIDA_DB)
    salvar_csv(limpos, SAIDA_CSV)
    print(f"  -> {SAIDA_DB}")
    print(f"  -> {SAIDA_CSV}")

    dropados_brutos = extrair_dropados(PLANILHA_ORIGEM)
    dropados_limpos = limpar_dropados(dropados_brutos)
    salvar_dropados(dropados_limpos, SAIDA_DB)
    print(f"  -> {len(dropados_limpos)} jogo(s) dropado(s) salvos")

    desafios_brutos = extrair_desafios(PLANILHA_ORIGEM)
    desafios_limpos = limpar_desafios(desafios_brutos)
    salvar_desafios(desafios_limpos, SAIDA_DB)
    print(f"  -> {len(desafios_limpos)} desafio(s) salvos")

    status_count = Counter(j.tempo_status for j in limpos)
    print("\nResumo da coluna 'Tempo':")
    for status, qtd in status_count.most_common():
        print(f"  {status:20s} {qtd}")

    if avisos:
        print(f"\n{len(avisos)} registro(s) precisam de revisão manual:")
        for aviso in avisos:
            print(f"  linha {aviso['linha_planilha']}: {aviso['jogo']} -> {aviso['problema']} ({aviso['valor_original']})")
    else:
        print("\nNenhum registro ficou sem interpretação. ✅")


if __name__ == "__main__":
    main()
