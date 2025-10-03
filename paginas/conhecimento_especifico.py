# paginas/conhecimento_especifico.py (ATUALIZADO)
import streamlit as st
import pandas as pd

# Importações conforme sua estrutura modular
from analysis import plot_performance_graph, show_best_hei_ranking_table
from utils import atualiza_cursos

def show_page(Enade_2023, UFPA_data, COURSE_CODES, hei_dict):
    """
    Página: Conhecimento Específico ENADE 2023
    Exibe filtros reativos, dois gráficos e a tabela de ranking.
    Agora os gráficos são renderizados como imagem em um wrapper .chart-fit
    para caberem na viewport sem exigir scroll.
    """

    with st.container():
        st.markdown("""
        <div class="text-container">
            <h1>Conhecimento Específico ENADE 2023</h1>
            <p>A análise gráfica fornece informações valiosas a respeito do desempenho dos alunos nas temáticas avaliadas na prova, uma vez que possibilita averiguar se as estratégias pedagógicas aplicadas nas disciplinas ministradas estão produzindo os resultados almejados. São apresentados dois gráficos que exibem a comparação entre o desempenho do curso de graduação da UFPA e o desempenho nacional, calculado a partir do mesmo curso ofertado por todas as IES no país que participam do exame.</p>
            <p>O Gráfico da Razão do Percentual de Acerto exibe o desempenho do curso da UFPA em comparação com a média nacional, por tema avaliado no ENADE 2023. A interpretação do gráfico da razão é a seguinte: Razão &gt; 1,0: a UFPA apresentou desempenho superior à média nacional; Razão &lt; 1,0: a UFPA obteve desempenho inferior à média nacional; Razão = 1,0: o desempenho da UFPA foi equivalente à média nacional.</p>
            <p>O Gráfico de Percentual de Acerto por Tema apresenta a comparação entre o percentual de acertos do curso da UFPA e o percentual médio nacional, para cada temática do componente específico da prova.</p>
            <p>Na Tabela Ranking é apresentada a instituição com melhor percentual de desempenho, por temática do exame, em comparação com o desempenho do curso da UFPA.</p>
        </div>
        """, unsafe_allow_html=True)

        # ----- Filtros reativos -----
        municipios = sorted(UFPA_data['NOME_MUNIC_CURSO'].unique().tolist())

        if 'municipio_op' not in st.session_state or st.session_state['municipio_op'] not in municipios:
            st.session_state['municipio_op'] = municipios[0]

        cursos_disponiveis = atualiza_cursos(UFPA_data, st.session_state['municipio_op'])
        if 'curso_op' not in st.session_state or st.session_state['curso_op'] not in cursos_disponiveis:
            st.session_state['curso_op'] = cursos_disponiveis[0]

        def atualizar_curso_selecionado():
            st.session_state['curso_op'] = atualiza_cursos(UFPA_data, st.session_state['municipio_op'])[0]

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.selectbox(
                "Selecione o Município",
                municipios,
                key='municipio_op',
                on_change=atualizar_curso_selecionado
            )

        with col2:
            st.selectbox(
                "Selecione o Curso",
                atualiza_cursos(UFPA_data, st.session_state['municipio_op']),
                key='curso_op'
            )

        with col3:
            st.write("")  # espaçamento
            st.write("")  # espaçamento
            public_only = st.checkbox(
                "Apenas IES Públicas",
                value=True,
                help="Filtra a tabela de ranking para comparar apenas com IES Públicas Federais."
            )

        # ----- Abas -----
        tab1, tab2, tab3 = st.tabs(["Gráfico Razão do Percentual", "Gráfico Percentual", "Tabela Ranking"])

        # ----- Localiza códigos do curso/grupo -----
        course_code = None
        group_code = None
        for code, details in COURSE_CODES.items():
            # details[1] = NOME_CURSO, details[3] = NOME_MUNIC_CURSO, details[0] = CO_GRUPO
            if details[1] == st.session_state['curso_op'] and details[3] == st.session_state['municipio_op']:
                course_code = code
                group_code = details[0]
                break

        if course_code and group_code:
            with st.spinner("Gerando análises..."):
                # Retorna (fig1, fig1_img, fig2, fig2_img)
                fig1, fig1_img, fig2, fig2_img = plot_performance_graph(
                    Enade_2023, COURSE_CODES, group_code, course_code
                )

                # Guarda caminhos/bytes para geração de PDF posterior
                st.session_state['razao_chart'] = fig1_img
                st.session_state['percent_chart'] = fig2_img

                # --------- Tab 1: Razão ----------
                with tab1:
                    if fig1_img:
                        # Imagem com auto-fit na viewport (usa .chart-fit do style.css)
                        st.markdown('<div class="chart-fit">', unsafe_allow_html=True)
                        st.image(fig1_img, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    elif fig1:
                        # Fallback: ainda permite renderizar a figura matplotlib
                        st.pyplot(fig1, use_container_width=True)
                    else:
                        st.warning("Não foi possível gerar o gráfico de razão para este curso.")

                # --------- Tab 2: Percentual ----------
                with tab2:
                    if fig2_img:
                        st.markdown('<div class="chart-fit">', unsafe_allow_html=True)
                        st.image(fig2_img, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    elif fig2:
                        st.pyplot(fig2, use_container_width=True)
                    else:
                        st.warning("Não foi possível gerar o gráfico de percentual para este curso.")

                # --------- Tab 3: Ranking ----------
                with tab3:
                    ranking_df = show_best_hei_ranking_table(
                        Enade_2023, COURSE_CODES, hei_dict, group_code, course_code, public_only
                    )
                    st.dataframe(ranking_df, use_container_width=True)
        else:
            st.warning("Não foi possível encontrar os detalhes para o curso selecionado. Verifique os dados.")
