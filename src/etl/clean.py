"""
Limpeza e normalização dos dados brutos extraídos da planilha.

A planilha foi preenchida manualmente ao longo de anos, então a coluna
"Tempo" sozinha tem pelo menos 5 formatos diferentes (célula de hora,
célula de duração, número puro em horas, texto com erro de digitação,
texto com "300+" indicando estimativa). Este módulo concentra toda
essa complexidade para que o resto do pipeline só lide com dados
já padronizados.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any

from .extract import DesafioBruto, JogoBruto, JogoDropadoBruto

# Correções conhecidas de digitação em nomes de console.
# Preferimos uma lista explícita a um "fuzzy match" automático:
# corrigir errado silenciosamente é pior do que não corrigir.
CORRECOES_CONSOLE = {
    "Xbos Series S": "Xbox Series S",
}


@dataclass
class JogoLimpo:
    linha_planilha: int
    ordem: int | None
    nome: str
    console: str
    genero: str
    tipo: str | None
    data: datetime.date | None
    tempo_horas: float | None
    tempo_status: str  # 'exato' | 'aproximado' | 'em_andamento' | 'ausente' | 'nao_reconhecido'
    tempo_bruto: str  # valor original, sempre preservado como texto
    nota: float | None
    dificuldade: str | None
    condicao_zeramento: str | None
    comentario_pessoal: str | None


def _parse_tempo(valor: Any) -> tuple[float | None, str]:
    """Converte qualquer um dos formatos de tempo da planilha em horas (float).

    Retorna (horas, status). `status` indica o nível de confiança:
    - 'exato': valor numérico direto, sem ambiguidade
    - 'formato_corrigido': texto com erro de digitação (ex: ';' em vez de ':')
    - 'em_andamento': jogo marcado como "contando" (ainda sendo jogado)
    - 'aproximado': valor com "+" (ex: "300+"), é um piso, não o total real
    - 'ausente': célula vazia
    - 'nao_reconhecido': não foi possível interpretar (fica None, mas nada é perdido)
    """
    if valor is None:
        return None, "ausente"

    if isinstance(valor, datetime.time):
        horas = valor.hour + valor.minute / 60 + valor.second / 3600
        return round(horas, 2), "exato"

    if isinstance(valor, datetime.timedelta):
        return round(valor.total_seconds() / 3600, 2), "exato"

    if isinstance(valor, (int, float)):
        # Na planilha, quando o tempo é digitado como número puro
        # (ex: 21, 737), o autor sempre quis dizer "horas".
        return round(float(valor), 2), "exato"

    if isinstance(valor, str):
        texto = valor.strip()

        aproximado = texto.endswith("+")
        em_andamento = "contando" in texto.lower()

        # extrai o primeiro trecho no formato h:mm(:ss), aceitando
        # ';' como separador por engano (erro de digitação comum na planilha)
        match = re.search(r"(\d+)[:;](\d{2})(?:[:;](\d{2}))?", texto)
        if match:
            h, m, s = match.groups()
            horas = int(h) + int(m) / 60 + (int(s) / 3600 if s else 0)
            if em_andamento:
                return round(horas, 2), "em_andamento"
            if ";" in texto:
                return round(horas, 2), "formato_corrigido"
            return round(horas, 2), "exato"

        # extrai só um número solto (ex: "300+")
        match_numero = re.search(r"(\d+)", texto)
        if match_numero:
            horas = float(match_numero.group(1))
            if aproximado:
                return horas, "aproximado"
            return horas, "formato_corrigido"

        return None, "nao_reconhecido"

    return None, "nao_reconhecido"


def _limpar_ordem(valor: Any) -> int | None:
    """A coluna 'ordem' vem de uma fórmula array (COUNTA) que às vezes
    retorna string vazia em vez de número, em linhas mais recentes da
    planilha. Tratamos isso como ausência de valor, não como erro."""
    if valor is None or valor == "":
        return None
    return int(valor)


def _limpar_console(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip()
    return CORRECOES_CONSOLE.get(texto, texto)


def _limpar_texto(valor: Any) -> str | None:
    """Remove espaços extras. Não mexe em maiúsculas/minúsculas nem
    tenta unificar categorias (ex: 'A' vs 'Fácil' na dificuldade) —
    isso é uma decisão de modelagem que cabe ao dono dos dados."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto if texto else None


@dataclass
class JogoDropadoLimpo:
    linha_planilha: int
    nome: str
    console: str
    nota: float | None


@dataclass
class DesafioLimpo:
    ano: int
    progresso: float
    descricao: str


def limpar_dropados(brutos: list[JogoDropadoBruto]) -> list[JogoDropadoLimpo]:
    return [
        JogoDropadoLimpo(
            linha_planilha=b.linha_planilha,
            nome=str(b.nome).strip(),
            console=_limpar_console(b.console),
            nota=float(b.nota) if b.nota is not None else None,
        )
        for b in brutos
    ]


def limpar_desafios(brutos: list[DesafioBruto]) -> list[DesafioLimpo]:
    limpos = []
    for b in brutos:
        # a planilha guarda progresso como fração (0 a 1); convertemos
        # para percentual (0 a 100), mais natural pra exibir num dashboard
        progresso = float(b.progresso) if b.progresso is not None else 0.0
        limpos.append(
            DesafioLimpo(
                ano=b.ano,
                progresso=round(min(progresso, 1.0) * 100, 1),
                descricao=_limpar_texto(b.descricao) or "",
            )
        )
    return limpos



def limpar_jogos(brutos: list[JogoBruto]) -> tuple[list[JogoLimpo], list[dict]]:
    """Aplica a limpeza em todos os registros.

    Retorna (jogos_limpos, avisos). `avisos` é a lista de problemas
    encontrados durante a limpeza (ex: tempo não reconhecido), pensada
    para virar um relatório legível — nenhum dado é descartado silenciosamente.
    """
    limpos: list[JogoLimpo] = []
    avisos: list[dict] = []

    for bruto in brutos:
        tempo_horas, tempo_status = _parse_tempo(bruto.tempo)

        if tempo_status == "nao_reconhecido":
            avisos.append(
                {
                    "linha_planilha": bruto.linha_planilha,
                    "jogo": bruto.nome,
                    "problema": "tempo não reconhecido",
                    "valor_original": repr(bruto.tempo),
                }
            )

        data_valor = bruto.data.date() if isinstance(bruto.data, datetime.datetime) else bruto.data

        limpos.append(
            JogoLimpo(
                linha_planilha=bruto.linha_planilha,
                ordem=_limpar_ordem(bruto.ordem),
                nome=str(bruto.nome).strip(),
                console=_limpar_console(bruto.console),
                genero=_limpar_texto(bruto.genero) or "",
                tipo=_limpar_texto(bruto.tipo),
                data=data_valor,
                tempo_horas=tempo_horas,
                tempo_status=tempo_status,
                tempo_bruto=str(bruto.tempo) if bruto.tempo is not None else "",
                nota=float(bruto.nota) if bruto.nota is not None else None,
                dificuldade=_limpar_texto(bruto.dificuldade),
                condicao_zeramento=_limpar_texto(bruto.condicao_zeramento),
                comentario_pessoal=_limpar_texto(bruto.comentario_pessoal),
            )
        )

    return limpos, avisos
