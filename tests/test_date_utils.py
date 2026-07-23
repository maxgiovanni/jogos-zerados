import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.date_utils import formatar_data_curta, formatar_data_extenso


def test_formatar_data_extenso_com_string_iso():
    assert formatar_data_extenso("2026-02-12") == "12 de fevereiro de 2026"


def test_formatar_data_curta_com_string_iso():
    assert formatar_data_curta("2026-02-12") == "12/02/2026"


def test_formatar_data_none_retorna_travessao():
    assert formatar_data_extenso(None) == "—"
    assert formatar_data_curta(None) == "—"


def test_formatar_data_string_vazia_retorna_travessao():
    assert formatar_data_extenso("") == "—"


def test_formatar_data_invalida_nao_quebra():
    assert formatar_data_extenso("não é uma data") == "—"
