"""
Formatação de datas em português brasileiro.

O Streamlit não tem suporte nativo a localização — o calendário do
`st.date_input` sempre mostra nomes de mês em inglês, isso é uma
limitação conhecida da própria ferramenta (sem solução simples até o
momento). O que dá pra controlar é o *formato numérico* do campo
(dd/mm/aaaa em vez de mm/dd/aaaa) e, principalmente, como exibimos
datas como texto no resto do app — isso sim fica 100% em português.
"""

from __future__ import annotations

import datetime

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


def formatar_data_extenso(data: str | datetime.date | None) -> str:
    """'2026-02-12' ou date(2026,2,12) -> '12 de fevereiro de 2026'."""
    data_obj = _para_date(data)
    if data_obj is None:
        return "—"
    return f"{data_obj.day} de {MESES_PT[data_obj.month]} de {data_obj.year}"


def formatar_data_curta(data: str | datetime.date | None) -> str:
    """'2026-02-12' ou date(2026,2,12) -> '12/02/2026'."""
    data_obj = _para_date(data)
    if data_obj is None:
        return "—"
    return data_obj.strftime("%d/%m/%Y")


def _para_date(data: str | datetime.date | None) -> datetime.date | None:
    if data is None or data == "":
        return None
    if isinstance(data, datetime.date):
        return data
    try:
        return datetime.date.fromisoformat(str(data)[:10])
    except ValueError:
        return None
