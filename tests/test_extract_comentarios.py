import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.etl.extract import extrair_comentarios_pessoais, extrair_jogos

PLANILHA = Path(__file__).resolve().parent.parent / "data" / "raw" / "Jogos_Zerados_-_Max.xlsx"


def test_extrai_comentarios_pessoais_da_planilha_real():
    comentarios = extrair_comentarios_pessoais(PLANILHA)
    assert len(comentarios) > 0
    # todo comentário extraído deve ter texto de verdade, não vazio
    assert all(texto.strip() for texto in comentarios.values())


def test_jogos_com_comentario_tem_o_campo_preenchido():
    jogos = extrair_jogos(PLANILHA)
    jogos_com_comentario = [j for j in jogos if j.comentario_pessoal]
    # a planilha real tem várias dezenas de comentários pessoais
    assert len(jogos_com_comentario) > 30
