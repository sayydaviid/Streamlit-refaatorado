import streamlit as st
import pandas as pd
from analysis import plot_performance_graph, show_best_hei_ranking_table
from utils import atualiza_cursos

def show_page(Enade_2023, UFPA_data, COURSE_CODES, hei_dict):
    # --- CSS PARA A ANIMAÇÃO DE CARREGAMENTO ---
    st.markdown("""
        <style>
        .loader-wrap {
            display: flex;
            width: 100%;
            height: 200px; /* Altura para centralizar no espaço da aba */
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
    """, unsafe_allow_html=True)

    # --- HTML DO LOADER ---
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

    st.markdown("""
         <div class="text-container">
            <h1>Conhecimento Específico ENADE 2023</h1>
            <p>A análise gráfica fornece informações valiosas a respeito do desempenho dos alunos nas temáticas avaliadas na prova, uma vez que possibilita averiguar se as estratégias pedagógicas aplicadas nas disciplinas ministradas estão produzindo os resultados almejados. São apresentados dois gráficos que exibem a comparação entre o desempenho do curso de graduação da UFPA e o desempenho nacional, calculado a partir do mesmo curso ofertado por todas as IES no país que participam do exame.</p>
            <p>O Gráfico da Razão do Percentual de Acerto exibe o desempenho do curso da UFPA em comparação com a média nacional, por tema avaliado no ENADE 2023. A interpretação do gráfico da razão é a seguinte: Razão > 1,0: a UFPA apresentou desempenho superior à média nacional; Razão < 1,0: a UFPA obteve desempenho inferior à média nacional; Razão = 1,0: o desempenho da UFPA foi equivalente à média nacional.</p>
            <p>O Gráfico de Percentual de Acerto por Tema apresenta a comparação entre o percentual de acertos do curso da UFPA e o percentual médio nacional, para cada temática do componente específico da prova.</p>
            <p>Na Tabela Ranking é apresentada a instituição com melhor percentual de desempenho, por temática do exame, em comparação com o desempenho do curso da UFPA.</p>
        </div>
        """, unsafe_allow_html=True)

    municipios = sorted(UFPA_data['NOME_MUNIC_CURSO'].unique().tolist())
    
    if 'municipio_op' not in st.session_state or st.session_state['municipio_op'] not in municipios:
        st.session_state['municipio_op'] = municipios[0]

    cursos_disponiveis = atualiza_cursos(UFPA_data, st.session_state['municipio_op'])
    if 'curso_op' not in st.session_state or st.session_state['curso_op'] not in cursos_disponiveis:
        st.session_state['curso_op'] = cursos_disponiveis[0]

    def atualizar_curso_selecionado():
        st.session_state['curso_op'] = atualiza_cursos(UFPA_data, st.session_state['municipio_op'])[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.selectbox("Selecione o Município", municipios, key='municipio_op', on_change=atualizar_curso_selecionado)

    with col2:
        st.selectbox('Selecione o Curso', atualiza_cursos(UFPA_data, st.session_state['municipio_op']), key='curso_op')
    
    tab1, tab2, tab3 = st.tabs(["Gráfico Razão do Percentual", "Gráfico Percentual", "Tabela Ranking"])

    course_code = None
    group_code = None
    for code, details in COURSE_CODES.items():
        if details[1] == st.session_state['curso_op'] and details[3] == st.session_state['municipio_op']:
            course_code = code
            group_code = details[0]
            break
    
    if course_code and group_code:
        with tab1:
            placeholder1 = st.empty()
            placeholder1.markdown(loader_html, unsafe_allow_html=True)
            
            fig1, fig1_img, _, _ = plot_performance_graph(Enade_2023, COURSE_CODES, group_code, course_code)
            st.session_state['razao_chart'] = fig1_img
            
            placeholder1.empty()  # Limpa o loader
            if fig1:
                st.pyplot(fig1)
            else:
                st.warning("Não foi possível gerar o gráfico de razão para este curso.")

        with tab2:
            placeholder2 = st.empty()
            placeholder2.markdown(loader_html, unsafe_allow_html=True)
            
            _, _, fig2, fig2_img = plot_performance_graph(Enade_2023, COURSE_CODES, group_code, course_code)
            st.session_state['percent_chart'] = fig2_img
            
            placeholder2.empty() # Limpa o loader
            if fig2:
                st.pyplot(fig2)
            else:
                st.warning("Não foi possível gerar o gráfico de percentual para este curso.")

        with tab3:
            placeholder3 = st.empty()
            placeholder3.markdown(loader_tabela_html, unsafe_allow_html=True)

            ranking_df = show_best_hei_ranking_table(
                Enade_2023, COURSE_CODES, hei_dict, group_code, course_code, public_only=True
            )
            
            column_config = {
                "Tema": st.column_config.Column(width="medium"),
                "IES com o melhor desempenho": st.column_config.Column(width="large"),
                "Nº de participantes": st.column_config.Column(width="small"),
                "Melhor curso (%)": st.column_config.NumberColumn(format="%.2f %%"),
                "UFPA (%)": st.column_config.NumberColumn(format="%.2f %%")
            }
            
            placeholder3.empty() # Limpa o loader
            st.dataframe(ranking_df, use_container_width=True, column_config=column_config)
    else:
        st.warning("Não foi possível encontrar os detalhes para o curso selecionado. Verifique os dados.")