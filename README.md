# 🎮 Jogos Zerados

Projeto pessoal que nasceu de uma planilha manual pra registrar todo jogo que eu zero — inspirada na planilha do [Cogumelando](https://www.youtube.com/@cogumelando) — e que estou evoluindo aos poucos para uma pipeline de dados em Python, como projeto de portfólio.

A ideia é simples: em vez de esconder o processo, o repositório documenta a evolução real, do jeito que ela aconteceu — da planilha manual em Excel/VBA até uma automação em Python com banco de dados, integração com API e dashboard.

## 📌 Sobre mim / contexto do projeto

Sou formado em Análise e Desenvolvimento de Sistemas, venho da área de TI (processos) e estou migrando para desenvolvimento/dados, estudando Python. Esse projeto é ao mesmo tempo um hobby (curto registrar os jogos que zero) e um exercício prático de portfólio.

## 🗺️ Roadmap / Versões

| Versão | Status | Descrição |
|---|---|---|
| **v1.0** | ✅ | Planilha original em Excel, como ela é hoje — dados reais, "sujos", com fórmulas e VBA manuais. Ponto de partida honesto do projeto. |
| **v2.0** | ✅ | Script Python de ETL: leitura do `.xlsx`, limpeza e padronização dos dados (formatos de tempo inconsistentes, categorias duplicadas, etc), saída em CSV/SQLite. |
| **v3.0** | 🔜 | Enriquecimento automático dos dados via API externa (IGDB/RAWG): capa, ano de lançamento, nota Metacritic. |
| **v4.0** | 🔜 | Dashboard interativo em Streamlit, substituindo a aba "Dashboard" manual da planilha. |
| **v5.0** | 💭 | Automação ponta a ponta (GitHub Actions) + exportação de volta para um `.xlsx` formatado. |

Cada versão é marcada como uma tag/release no repositório, então dá pra acompanhar a evolução pelo histórico do Git.

## 📁 Estrutura do projeto

```
jogos-zerados/
├── data/
│   ├── raw/          # dados originais, sem tratamento (a planilha "crua")
│   └── processed/    # dados já limpos/tratados pelo pipeline Python
├── src/               # código-fonte: ETL, integração com API, banco de dados
├── notebooks/         # exploração de dados (Jupyter)
├── dashboard/          # app Streamlit
├── tests/              # testes automatizados
└── README.md
```

## 📊 v1.0 — A planilha original

O arquivo em `data/raw/Jogos_Zerados_-_Max.xlsx` é a planilha manual que uso desde antes de começar esse projeto. Ela contém:

- **Jogos Zerados**: lista principal com jogo, console, gênero, tipo, data, tempo de jogo, nota e condição de zeramento.
- **Jogos Dropados**: jogos que comecei e não terminei.
- **Desafios**: metas anuais (ex: "zerar toda a franquia God of War").
- **Dashboard**: contagem manual de jogos por gênero via fórmulas.

É uma planilha real de uso pessoal — com inconsistências (formatos de tempo diferentes, categorias duplicadas por espaço extra, etc) que serão o ponto de partida para o trabalho de limpeza de dados nas próximas versões.

## ⚙️ v2.0 — Pipeline de ETL em Python

O script em `src/run_etl.py` lê a planilha original, limpa os dados e gera uma versão tratada em `data/processed/` (SQLite + CSV).

### Principais problemas de dados resolvidos

- **Formatos de tempo inconsistentes**: a coluna "Tempo" continha 5 formatos diferentes (célula de hora, célula de duração acima de 24h, número puro representando horas, texto com erro de digitação como `"09;33:56"`, e texto com estimativa como `"300+"`). Todos foram convertidos para horas em ponto flutuante, preservando o valor original e um status de confiança (`exato`, `formato_corrigido`, `aproximado`, `em_andamento`, `ausente`, `nao_reconhecido`).
- **Erros de digitação em console**: ex. `"Xbos Series S"` → `"Xbox Series S"`.
- **Espaços extras em texto**: ex. `"Ação "` → `"Ação"` (a planilha original contava "Ação" e "Ação " como categorias diferentes no dashboard).
- **Coluna "Dificuldade" com duas escalas misturadas** (`Fácil`/`Médio` e `A`/`AA`/`B`): os espaços foram normalizados, mas a unificação das escalas foi deixada como decisão manual — não faz sentido o script "adivinhar" uma correspondência entre as duas.

Nenhum dado é descartado silenciosamente: qualquer valor que o script não conseguir interpretar aparece no relatório final da execução.

### Como rodar

```bash
pip install -r requirements.txt
python -m src.run_etl
```

### Como rodar os testes

```bash
pytest tests/
```

## 🛠️ Tecnologias planejadas

- Python (pandas, openpyxl)
- SQLite + SQLAlchemy
- Streamlit
- GitHub Actions (CI)

## 📄 Licença

MIT
