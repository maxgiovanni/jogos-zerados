"""
Dashboard "Jogos Zerados" — v4.1

Biblioteca pessoal de jogos zerados, inspirada em Steam/HowLongToBeat:
grade de capas, tela de detalhes, cadastro e edição de jogos, e CRUD de
desafios anuais. Sempre que um jogo é criado ou editado por aqui, o
Excel em data/processed/Jogos_Zerados_atualizado.xlsx é regenerado.

Como rodar:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src import repository
from src.date_utils import formatar_data_curta, formatar_data_extenso
from src.enrichment.enrich import enriquecer_jogo_por_id
from src.export.xlsx_writer import exportar_para_xlsx

load_dotenv(RAIZ / ".env")

BANCO = RAIZ / "data" / "processed" / "jogos_zerados.db"
XLSX_ATUALIZADO = RAIZ / "data" / "processed" / "Jogos_Zerados_atualizado.xlsx"
CAPA_PADRAO = "https://placehold.co/300x400?text=Sem+capa"
ALTURA_CAPA_PX = 260

OPCOES_DIFICULDADE = ["Fácil", "Médio", "Difícil"]

st.set_page_config(page_title="Jogos Zerados", page_icon="🎮", layout="wide")


def _sincronizar_xlsx() -> None:
    exportar_para_xlsx(BANCO, XLSX_ATUALIZADO)


def _capa_html(url: str | None, altura: int = ALTURA_CAPA_PX) -> str:
    """Gera uma capa com tamanho sempre igual, não importa a resolução
    original da imagem (usa object-fit: cover, técnica de CSS que
    recorta a imagem mantendo a proporção, em vez de esticar/distorcer)."""
    return (
        f'<div style="width:100%;height:{altura}px;overflow:hidden;'
        f'border-radius:8px;background:#222;">'
        f'<img src="{url or CAPA_PADRAO}" '
        f'style="width:100%;height:100%;object-fit:cover;display:block;">'
        f'</div>'
    )


def _formulario_jogo(dados_iniciais: dict | None = None, key_prefix: str = "novo") -> dict | None:
    dados_iniciais = dados_iniciais or {}

    with st.form(key=f"{key_prefix}_form"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do jogo", value=dados_iniciais.get("nome", ""))
            console = st.text_input("Console", value=dados_iniciais.get("console", ""))
            genero = st.text_input("Gênero", value=dados_iniciais.get("genero", ""))
            tipo = st.text_input("Tipo", value=dados_iniciais.get("tipo", ""))
        with col2:
            data = st.date_input("Data de zeramento", value=None, format="DD/MM/YYYY")
            tempo_horas = st.number_input(
                "Tempo de jogo (horas)", min_value=0.0, step=0.5,
                value=float(dados_iniciais.get("tempo_horas") or 0.0),
            )
            nota = st.slider("Sua nota", 0.0, 11.0, float(dados_iniciais.get("nota") or 7.0), step=0.5)
            dificuldade_atual = dados_iniciais.get("dificuldade")
            dificuldade = st.selectbox(
                "Dificuldade", OPCOES_DIFICULDADE,
                index=OPCOES_DIFICULDADE.index(dificuldade_atual) if dificuldade_atual in OPCOES_DIFICULDADE else 0,
            )

        condicao_zeramento = st.text_input(
            "Condição de zeramento",
            value=dados_iniciais.get("condicao_zeramento", ""),
            placeholder="Ex: História + 100%, Platina, etc.",
        )
        comentario_pessoal = st.text_area(
            "Sua opinião / comentário sobre o jogo",
            value=dados_iniciais.get("comentario_pessoal", ""),
            placeholder="Espaço livre pra escrever o que quiser sobre a experiência com o jogo.",
            height=120,
        )

        enviado = st.form_submit_button("💾 Salvar")

    if not enviado:
        return None

    if not nome.strip():
        st.error("O nome do jogo é obrigatório.")
        return None

    return {
        "nome": nome.strip(),
        "console": console.strip(),
        "genero": genero.strip(),
        "tipo": tipo.strip() or None,
        "data": data.isoformat() if data else None,
        "tempo_horas": tempo_horas,
        "tempo_status": "exato",
        "tempo_bruto": str(tempo_horas),
        "nota": nota,
        "dificuldade": dificuldade,
        "condicao_zeramento": condicao_zeramento.strip() or None,
        "comentario_pessoal": comentario_pessoal.strip() or None,
    }


def pagina_adicionar() -> None:
    st.title("➕ Adicionar jogo zerado")
    st.caption("Preenche igualzinho você fazia na planilha — só que agora com validação e busca automática de capa.")

    dados = _formulario_jogo(key_prefix="novo")
    if dados is None:
        return

    existente = repository.jogo_existe(BANCO, dados["nome"], dados["console"])
    if existente:
        st.warning(
            f"⚠️ '{dados['nome']}' já está cadastrado nesse console. "
            f"Pra evitar duplicata, não vou criar um registro novo — "
            f"se quer corrigir algo, use a opção 'Editar' na tela de detalhes desse jogo."
        )
        return

    jogo_id = repository.inserir_jogo(BANCO, dados)
    st.success(f"'{dados['nome']}' cadastrado!")

    with st.spinner("Buscando capa e informações na RAWG..."):
        resultado = enriquecer_jogo_por_id(BANCO, jogo_id, dados["nome"])

    if resultado.erro:
        st.warning(f"Não foi possível buscar na RAWG agora: {resultado.erro}")
    elif not resultado.encontrado:
        st.info("Jogo cadastrado, mas não encontrado na RAWG (capa ficará em branco).")
    else:
        st.success("Capa e dados da RAWG encontrados!")

    _sincronizar_xlsx()
    st.caption(f"Excel atualizado em: {XLSX_ATUALIZADO}")

    if st.button("Ver na biblioteca"):
        st.session_state.pagina = "detalhes"
        st.session_state.jogo_selecionado = jogo_id
        st.rerun()


def pagina_editar(jogo_id: int) -> None:
    jogo = repository.obter_jogo(BANCO, jogo_id)
    if jogo is None:
        st.error("Jogo não encontrado.")
        return

    st.title(f"✏️ Editando: {jogo['nome']}")

    dados = _formulario_jogo(dados_iniciais=jogo, key_prefix=f"editar_{jogo_id}")
    if dados is None:
        if st.button("← Voltar sem salvar"):
            st.session_state.pagina = "detalhes"
            st.rerun()
        return

    repository.atualizar_jogo(BANCO, jogo_id, dados)
    _sincronizar_xlsx()
    st.success("Alterações salvas!")
    st.session_state.pagina = "detalhes"
    st.rerun()


def pagina_detalhes(jogo_id: int) -> None:
    jogo = repository.obter_jogo(BANCO, jogo_id)
    if jogo is None:
        st.error("Jogo não encontrado.")
        return

    if st.button("← Voltar pra biblioteca"):
        st.session_state.pagina = "biblioteca"
        st.session_state.jogo_selecionado = None
        st.rerun()

    col_capa, col_info = st.columns([1, 2])
    with col_capa:
        st.markdown(_capa_html(jogo.get("capa_url"), altura=380), unsafe_allow_html=True)
    with col_info:
        st.title(jogo["nome"])
        st.caption(f"{jogo.get('console') or '—'} · {jogo.get('genero') or '—'}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Sua nota", jogo.get("nota") or "—")
        c2.metric("Tempo", f"{jogo['tempo_horas']:.1f}h" if jogo.get("tempo_horas") else "—")
        c3.metric("Metacritic", jogo.get("nota_metacritic") or "—")

        st.write(f"**Dificuldade:** {jogo.get('dificuldade') or '—'}")
        st.write(f"**Data de zeramento:** {formatar_data_extenso(jogo.get('data'))}")
        st.write(f"**Lançamento (RAWG):** {formatar_data_extenso(jogo.get('rawg_lancamento'))}")

        if jogo.get("condicao_zeramento"):
            st.write(f"**Condição de zeramento:** {jogo['condicao_zeramento']}")

        if jogo.get("comentario_pessoal"):
            st.write("**Sua opinião:**")
            st.info(jogo["comentario_pessoal"])

        if st.button("✏️ Editar este jogo"):
            st.session_state.pagina = "editar"
            st.rerun()


def pagina_biblioteca() -> None:
    st.title("🎮 Minha biblioteca de jogos zerados")

    jogos = repository.listar_jogos(BANCO)
    if not jogos:
        st.info("Nenhum jogo cadastrado ainda. Use o menu lateral pra adicionar o primeiro!")
        return

    busca = st.text_input("🔎 Buscar por nome")
    if busca:
        jogos = [j for j in jogos if busca.lower() in j["nome"].lower()]

    st.caption(f"{len(jogos)} jogo(s)")

    colunas = st.columns(5)
    for i, jogo in enumerate(jogos):
        with colunas[i % 5]:
            st.markdown(_capa_html(jogo.get("capa_url")), unsafe_allow_html=True)
            st.caption(jogo["nome"])
            tempo_texto = f"{jogo['tempo_horas']:.0f}h" if jogo.get("tempo_horas") else "—"
            st.caption(f"🎮 {jogo.get('console') or '—'}  ·  ⏱️ {tempo_texto}")
            if st.button("Ver detalhes", key=f"ver_{jogo['id']}"):
                st.session_state.pagina = "detalhes"
                st.session_state.jogo_selecionado = jogo["id"]
                st.rerun()


def pagina_dropados() -> None:
    st.title("🗑️ Jogos dropados")
    st.caption("Jogos que você começou mas não terminou — também fazem parte da jornada.")

    dropados = repository.listar_dropados(BANCO)
    if not dropados:
        st.info("Nenhum jogo dropado registrado.")
        return

    for jogo in dropados:
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{jogo['nome']}**")
        c2.write(jogo.get("console") or "—")
        c3.write(f"nota: {jogo.get('nota') or '—'}")


def pagina_desafios() -> None:
    st.title("🏆 Desafios")

    with st.expander("➕ Novo desafio"):
        with st.form("novo_desafio_form"):
            c1, c2 = st.columns([1, 3])
            ano = c1.number_input("Ano", min_value=2000, max_value=2100, value=2026, step=1)
            descricao = c2.text_input("Descrição da meta")
            progresso = st.slider("Progresso inicial (%)", 0, 100, 0)
            if st.form_submit_button("Adicionar") and descricao.strip():
                repository.inserir_desafio(BANCO, int(ano), descricao.strip(), float(progresso))
                st.success("Desafio adicionado!")
                st.rerun()

    desafios = repository.listar_desafios(BANCO)
    if not desafios:
        st.info("Nenhum desafio registrado.")
        return

    anos = sorted({d["ano"] for d in desafios}, reverse=True)
    for ano in anos:
        st.subheader(str(ano))
        for desafio in [d for d in desafios if d["ano"] == ano]:
            chave_edicao = f"editando_desafio_{desafio['id']}"

            if st.session_state.get(chave_edicao):
                with st.form(f"editar_desafio_{desafio['id']}"):
                    nova_descricao = st.text_input("Descrição", value=desafio["descricao"])
                    novo_progresso = st.slider("Progresso (%)", 0, 100, int(desafio["progresso"]))
                    col_salvar, col_cancelar = st.columns(2)
                    if col_salvar.form_submit_button("💾 Salvar"):
                        repository.atualizar_desafio(BANCO, desafio["id"], nova_descricao.strip(), float(novo_progresso))
                        st.session_state[chave_edicao] = False
                        st.rerun()
                    if col_cancelar.form_submit_button("Cancelar"):
                        st.session_state[chave_edicao] = False
                        st.rerun()
                continue

            col_desc, col_editar, col_excluir = st.columns([5, 1, 1])
            with col_desc:
                st.write(desafio["descricao"])
                st.progress(min(int(desafio["progresso"]), 100) / 100)
            with col_editar:
                if st.button("✏️", key=f"editar_{desafio['id']}"):
                    st.session_state[chave_edicao] = True
                    st.rerun()
            with col_excluir:
                if st.button("🗑️", key=f"excluir_{desafio['id']}"):
                    repository.excluir_desafio(BANCO, desafio["id"])
                    st.rerun()


def main() -> None:
    if not BANCO.exists():
        st.error(
            "Banco de dados não encontrado. Rode primeiro:\n\n"
            "```\npython -m src.run_etl\npython -m src.run_enrich\n```"
        )
        return

    st.session_state.setdefault("pagina", "biblioteca")
    st.session_state.setdefault("jogo_selecionado", None)

    st.sidebar.title("🎮 Jogos Zerados")
    opcao = st.sidebar.radio(
        "Menu",
        ["Biblioteca", "Adicionar jogo", "Dropados", "Desafios"],
        index=0,
    )

    mapa_menu = {
        "Biblioteca": "biblioteca",
        "Adicionar jogo": "adicionar",
        "Dropados": "dropados",
        "Desafios": "desafios",
    }
    pagina_via_menu = mapa_menu[opcao]

    if pagina_via_menu != st.session_state.get("ultima_opcao_menu"):
        st.session_state.pagina = pagina_via_menu
        st.session_state.ultima_opcao_menu = pagina_via_menu

    pagina = st.session_state.pagina

    if pagina == "adicionar":
        pagina_adicionar()
    elif pagina == "dropados":
        pagina_dropados()
    elif pagina == "desafios":
        pagina_desafios()
    elif pagina == "detalhes" and st.session_state.jogo_selecionado:
        pagina_detalhes(st.session_state.jogo_selecionado)
    elif pagina == "editar" and st.session_state.jogo_selecionado:
        pagina_editar(st.session_state.jogo_selecionado)
    else:
        pagina_biblioteca()


if __name__ == "__main__":
    main()
