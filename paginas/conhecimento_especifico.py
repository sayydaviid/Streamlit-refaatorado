# paginas/conhecimento_especifico.py
# (LIMPO: APENAS 2023)

import streamlit as st
import pandas as pd
from analysis import plot_performance_graph, show_best_hei_ranking_table
from utils import atualiza_cursos

def show_page(Enade, UFPA_data, COURSE_CODES, hei_dict):
    # --- CSS PARA A ANIMAÇÃO DE CARREGAMENTO ---
    st.markdown(
        """
        <style>
        .loader-wrap {
            display: flex;
            width: 100%;
            height: 200px;
            align-items: center;
            justify-content: center;
            gap: .75rem;
            color: #4A4A4A;
        }
        .lds-ring {
            display: inline-block;
            position: relative;
            width: 30px;
            height: 30px;
        }
        .lds-ring div {
            box-sizing: border-box;
            display: block;
            position: absolute;
            width: 30px;
            height: 30px;
            border: 4px solid #2E5C8A;
            border-radius: 50%;
            animation: lds-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
            border-color: #2E5C8A transparent transparent transparent;
        }
        .lds-ring div:nth-child(1) { animation-delay: -0.45s; }
        .lds-ring div:nth-child(2) { animation-delay: -0.3s; }
        .lds-ring div:nth-child(3) { animation-delay: -0.15s; }
        @keyframes lds-ring {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    loader_html = """
        <div class="loader-wrap">
            <span class="lds-ring"><div></div><div></div><div></div><div></div></span>
            <span>Gerando gráfico...</span>
        </div>
    """
    loader_tabela_html = """
        <div class="loader-wrap">
            <span class="lds-ring"><div></div><div></div><div></div><div></div></span>
            <span>Gerando tabela...</span>
        </div>
    """

    # ---------------------------------------------------------
    # Cabeçalho
    # ---------------------------------------------------------
    st.markdown(
        """
         <div class="text-container">
            <h1>Conhecimento Específico ENADE</h1>
            <p>
                A análise gráfica fornece informações valiosas a respeito do desempenho dos alunos nas temáticas avaliadas
                na prova, uma vez que possibilita averiguar se as estratégias pedagógicas aplicadas nas disciplinas ministradas
                estão produzindo os resultados almejados. São apresentados dois gráficos que exibem a comparação entre o desempenho
                do curso de graduação da UFPA e o desempenho nacional, calculado a partir do mesmo curso ofertado por todas as IES no
                país que participam do exame.
            </p>
            <p>
                O Gráfico da Razão do Percentual de Acerto exibe o desempenho do curso da UFPA em comparação com a média nacional.
                A interpretação do gráfico da razão é a seguinte: Razão &gt; 1,0: desempenho superior; Razão &lt; 1,0: desempenho inferior;
                Razão = 1,0: equivalente à média nacional.
            </p>
            <p>
                O Gráfico de Percentual de Acerto por Tema apresenta a comparação entre o percentual de acertos do curso da UFPA e o percentual
                médio nacional, para cada temática do componente específico.
            </p>
            <p>
                Na Tabela Ranking é apresentada a instituição com melhor percentual de desempenho, por temática do exame, em comparação com o
                desempenho do curso da UFPA.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # Edição (Fixa 2023) + Município + Curso
    # ---------------------------------------------------------
    
    # Define estritamente 2023
    edicoes_disponiveis = ["2023"]

    if "edicao_op" not in st.session_state or st.session_state["edicao_op"] not in edicoes_disponiveis:
        st.session_state["edicao_op"] = "2023"

    def on_change_edicao():
        st.session_state.pop("municipio_op", None)
        st.session_state.pop("curso_op", None)

    col_ed, col_mun, col_cur = st.columns(3)
    with col_ed:
        st.selectbox(
            "Selecione a Edição",
            edicoes_disponiveis,
            key="edicao_op",
            on_change=on_change_edicao,
            disabled=True # Travado em 2023
        )

    # Filtra Dataframes para 2023
    if "EDICAO" in Enade.columns:
        Enade_filtrado = Enade[Enade["EDICAO"].astype(str) == "2023"].copy()
    elif "NU_ANO" in Enade.columns:
        Enade_filtrado = Enade[Enade["NU_ANO"].astype(str) == "2023"].copy()
    else:
        Enade_filtrado = Enade.copy()

    if "EDICAO" in UFPA_data.columns:
        UFPA_filtrado = UFPA_data[UFPA_data["EDICAO"].astype(str) == "2023"].copy()
    elif "NU_ANO" in UFPA_data.columns:
        UFPA_filtrado = UFPA_data[UFPA_data["NU_ANO"].astype(str) == "2023"].copy()
    else:
        UFPA_filtrado = UFPA_data.copy()

    if UFPA_filtrado.empty:
        st.warning("Não há dados da UFPA para a edição de 2023.")
        return

    # Lógica de Municípios e Cursos
    municipios = sorted(UFPA_filtrado["NOME_MUNIC_CURSO"].dropna().unique().tolist())
    if not municipios:
        st.warning("Não foi possível listar municípios com os dados atuais.")
        return

    if "municipio_op" not in st.session_state or st.session_state["municipio_op"] not in municipios:
        st.session_state["municipio_op"] = municipios[0]

    cursos_disponiveis = atualiza_cursos(UFPA_filtrado, st.session_state["municipio_op"])
    if not cursos_disponiveis:
        st.warning("Não há cursos disponíveis para o município selecionado nesta edição.")
        return

    if "curso_op" not in st.session_state or st.session_state["curso_op"] not in cursos_disponiveis:
        st.session_state["curso_op"] = cursos_disponiveis[0]

    def atualizar_curso_selecionado():
        cursos = atualiza_cursos(UFPA_filtrado, st.session_state["municipio_op"])
        st.session_state["curso_op"] = cursos[0] if cursos else None

    with col_mun:
        st.selectbox(
            "Selecione o Município",
            municipios,
            key="municipio_op",
            on_change=atualizar_curso_selecionado,
        )

    with col_cur:
        st.selectbox(
            "Selecione o Curso",
            atualiza_cursos(UFPA_filtrado, st.session_state["municipio_op"]),
            key="curso_op",
        )

    # ---------------------------------------------------------
    # Tabs
    # ---------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(
        ["Gráfico Razão do Percentual", "Gráfico Percentual", "Tabela Ranking"]
    )

    # Mapeia (nome curso, município) -> course_code e group_code
    course_code = None
    group_code = None
    for code, details in COURSE_CODES.items():
        if details[1] == st.session_state["curso_op"] and details[3] == st.session_state["municipio_op"]:
            course_code = code
            group_code = details[0]
            break

    if not course_code or not group_code:
        st.warning("Não foi possível encontrar os detalhes para o curso selecionado. Verifique os dados.")
        return

    # ---------------------------------------------------------
    # Renderizações
    # ---------------------------------------------------------
    with tab1:
        placeholder1 = st.empty()
        placeholder1.markdown(loader_html, unsafe_allow_html=True)

        fig1, fig1_img, _, _ = plot_performance_graph(Enade_filtrado, COURSE_CODES, group_code, course_code)
        st.session_state["razao_chart"] = fig1_img

        placeholder1.empty()
        if fig1:
            st.pyplot(fig1)
        else:
            st.warning("Não foi possível gerar o gráfico de razão para este curso.")

    with tab2:
        placeholder2 = st.empty()
        placeholder2.markdown(loader_html, unsafe_allow_html=True)

        _, _, fig2, fig2_img = plot_performance_graph(Enade_filtrado, COURSE_CODES, group_code, course_code)
        st.session_state["percent_chart"] = fig2_img

        placeholder2.empty()
        if fig2:
            st.pyplot(fig2)
        else:
            st.warning("Não foi possível gerar o gráfico de percentual para este curso.")

    with tab3:
        placeholder3 = st.empty()
        placeholder3.markdown(loader_tabela_html, unsafe_allow_html=True)

        ranking_df = show_best_hei_ranking_table(
            Enade_filtrado, COURSE_CODES, hei_dict, group_code, course_code, public_only=True
        )

        column_config = {
            "Tema": st.column_config.Column(width="medium"),
            "IES com o melhor desempenho": st.column_config.Column(width="large"),
            "Nº de participantes": st.column_config.Column(width="small"),
            "Melhor curso (%)": st.column_config.NumberColumn(format="%.2f %%"),
            "UFPA (%)": st.column_config.NumberColumn(format="%.2f %%"),
        }

        placeholder3.empty()
        st.dataframe(ranking_df, use_container_width=True, column_config=column_config)