"""
Testes do módulo de limpeza — principalmente do parser de tempo,
que é a parte mais arriscada do ETL por causa da quantidade de
formatos diferentes que a planilha acumulou ao longo dos anos.
"""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.etl.clean import _parse_tempo, _limpar_console, _limpar_texto


def test_tempo_ausente():
    horas, status = _parse_tempo(None)
    assert horas is None
    assert status == "ausente"


def test_tempo_como_objeto_time():
    horas, status = _parse_tempo(datetime.time(4, 30))
    assert horas == 4.5
    assert status == "exato"


def test_tempo_como_timedelta_maior_que_um_dia():
    # 1 dia + 8h15m53s ~ 32.26h (caso real: "Pentiment")
    horas, status = _parse_tempo(datetime.timedelta(days=1, hours=8, minutes=15, seconds=53))
    assert round(horas, 1) == 32.3
    assert status == "exato"


def test_tempo_como_numero_puro():
    # caso real: "GTA V" = 737
    horas, status = _parse_tempo(737)
    assert horas == 737.0
    assert status == "exato"


def test_tempo_com_erro_de_digitacao_ponto_e_virgula():
    # caso real: "UFC 4" = "09;33:56"
    horas, status = _parse_tempo("09;33:56")
    assert round(horas, 2) == 9.57
    assert status == "formato_corrigido"


def test_tempo_em_andamento():
    # caso real: "Skate 3" = "18:29:10 (contando)"
    horas, status = _parse_tempo("18:29:10 (contando)")
    assert round(horas, 2) == 18.49
    assert status == "em_andamento"


def test_tempo_aproximado_com_mais():
    # caso real: "Battlefield 4" = "300+"
    horas, status = _parse_tempo("300+")
    assert horas == 300.0
    assert status == "aproximado"


def test_tempo_nao_reconhecido_nao_quebra_o_pipeline():
    horas, status = _parse_tempo("isso não é um tempo válido")
    assert horas is None
    assert status == "nao_reconhecido"


def test_correcao_de_console_conhecida():
    assert _limpar_console("Xbos Series S") == "Xbox Series S"


def test_console_sem_erro_permanece_igual():
    assert _limpar_console("PS5") == "PS5"


def test_limpar_texto_remove_espacos_extras():
    assert _limpar_texto("Ação ") == "Ação"


def test_limpar_texto_valor_vazio_vira_none():
    assert _limpar_texto("   ") is None
    assert _limpar_texto(None) is None
