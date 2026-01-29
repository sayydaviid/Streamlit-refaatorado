# paginas/questionario_do_estudante.py (LIMPO: APENAS 2023)

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

from utils import atualiza_cursos
from analysis import plot_average_graph, plot_count_graph


def show_page(QE_data, UFPA_data, COURSE_CODES):
    with st.container():
        st.markdown(
            """
        <div class="text-container">
            <h1>Questionário do Estudante ENADE</h1>
            <p>
                Para cada questão no Questionário do Estudante, são disponibilizadas 6 alternativas de resposta que indicam
                o grau de concordância com cada assertiva, em uma escala que varia de 1 (discordância total) a 6 (concordância total),
                além das alternativas 7 (Não sei responder) e 8 (Não se aplica).
            </p>
            <p>
                Para cada dimensão do questionário, foram gerados dois gráficos. O gráfico de barras apresenta a média atribuída
                pelos alunos para cada questão, excluídas as alternativas 7 e 8. São destacadas as questões com a maior e a menor média.
            </p>
            <p>
                O gráfico de linhas representa, por questão, o total de respostas absolutas (contagem) agrupadas pelo tipo de alternativa
                escolhida, da seguinte forma: 1-2; 3-4; 5-6; 7-8.
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

        if "edicao_op_qe" not in st.session_state or st.session_state["edicao_op_qe"] not in edicoes_disponiveis:
            st.session_state["edicao_op_qe"] = "2023"

        def on_change_edicao_qe():
            st.session_state.pop("municipio_op_qe", None)
            st.session_state.pop("curso_op_qe", None)

        col_ed, col_mun, col_cur = st.columns(3)

        with col_ed:
            st.selectbox(
                "Selecione a Edição",
                edicoes_disponiveis,
                key="edicao_op_qe",
                on_change=on_change_edicao_qe,
                disabled=True # Travado em 2023
            )

        # Filtra Dataframes para 2023
        # Verifica se a coluna é EDICAO ou NU_ANO para garantir compatibilidade
        if "EDICAO" in QE_data.columns:
            QE_filtrado = QE_data[QE_data["EDICAO"].astype(str) == "2023"].copy()
        elif "NU_ANO" in QE_data.columns:
            QE_filtrado = QE_data[QE_data["NU_ANO"].astype(str) == "2023"].copy()
        else:
            QE_filtrado = QE_data.copy()

        if "EDICAO" in UFPA_data.columns:
            UFPA_filtrado = UFPA_data[UFPA_data["EDICAO"].astype(str) == "2023"].copy()
        elif "NU_ANO" in UFPA_data.columns:
            UFPA_filtrado = UFPA_data[UFPA_data["NU_ANO"].astype(str) == "2023"].copy()
        else:
            UFPA_filtrado = UFPA_data.copy()

        if UFPA_filtrado.empty:
            st.warning("Não há dados da UFPA para a edição de 2023.")
            return

        # Lógica de Municípios
        municipios = sorted(UFPA_filtrado["NOME_MUNIC_CURSO"].dropna().unique().tolist())
        if not municipios:
            st.warning("Não foi possível listar municípios com os dados atuais.")
            return

        if "municipio_op_qe" not in st.session_state or st.session_state["municipio_op_qe"] not in municipios:
            st.session_state["municipio_op_qe"] = municipios[0]

        cursos_disponiveis = atualiza_cursos(UFPA_filtrado, st.session_state["municipio_op_qe"])
        if not cursos_disponiveis:
            st.warning("Não há cursos disponíveis para o município selecionado nesta edição.")
            return

        if "curso_op_qe" not in st.session_state or st.session_state["curso_op_qe"] not in cursos_disponiveis:
            st.session_state["curso_op_qe"] = cursos_disponiveis[0]

        def atualizar_curso_selecionado_qe():
            cursos = atualiza_cursos(UFPA_filtrado, st.session_state["municipio_op_qe"])
            st.session_state["curso_op_qe"] = cursos[0] if cursos else None

        with col_mun:
            st.selectbox(
                "Selecione o Município",
                municipios,
                key="municipio_op_qe",
                on_change=atualizar_curso_selecionado_qe,
            )

        with col_cur:
            st.selectbox(
                "Selecione o Curso",
                atualiza_cursos(UFPA_filtrado, st.session_state["municipio_op_qe"]),
                key="curso_op_qe",
            )

        # ---------------------------------------------------------
        # Tabs
        # ---------------------------------------------------------
        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "Organização Didático-Pedagógica",
                "Infraestrutura e Instalações Físicas",
                "Ampliação da Formação",
                "Visualizar Questionário",
            ]
        )

        # ---------------------------------------------------------
        # Questões e textos
        # ---------------------------------------------------------
        odp_questions_text = [
            "As disciplinas cursadas contribuíram para sua formação integral, como cidadão e profissional.",
            "Os conteúdos abordados nas disciplinas do curso favoreceram sua atuaçãoem estágios ou em atividades de iniciação profissional.",
            "As metodologias de ensino utilizadas no curso desafiaram você a aprofundar conhecimentos e desenvolver competênciasreflexivas e críticas.",
            "O curso propiciou experiências de aprendizagem inovadoras.",
            "O curso contribuiu para o desenvolvimento da sua consciência ética para o exercício profissional.",
            "No curso você teve oportunidade de aprender a trabalhar em equipe.",
            "O curso possibilitou aumentar sua capacidade de reflexão e argumentação.",
            "O curso promoveu o desenvolvimento da sua capacidade de pensar criticamente, analisar e refletir sobre soluções para problemas da sociedade.",
            "O curso contribuiu para você ampliar sua capacidade de comunicação nas formas oral e escrita.",
            "O curso contribuiu para o desenvolvimento da sua capacidade de aprender e atualizar-se permanentemente.",
            "As relações professor-aluno ao longo do curso estimularam você a estudar e aprender.",
            "Os planos de ensino apresentados pelos professores contribuíram para o desenvolvimento das atividades acadêmicas e para seus estudos.",
            "As referências bibliográficas indicadas pelos professores nosplanos de ensino contribuíram para seus estudos e aprendizagens.",
            "Foram oferecidas oportunidades para os estudantes superarem dificuldades relacionadas ao processo de formação.",
            "O curso exigiu de você organização e dedicação frequente aos estudos.",
            "O curso favoreceu a articulação do conhecimento teórico com atividades práticas.",
            "As atividades práticas foram suficientes para relacionar os conteúdos do curso com a prática, contribuindo para sua formação profissional.",
            "O curso propiciou acesso a conhecimentos atualizados e/ou contemporâneos em sua área de formação.",
            "As atividades realizadas durante seu trabalho de conclusão de curso contribuíram para qualificar sua formação profissional.",
            "As avaliações da aprendizagem realizadas durante o curso foram compatíveis com os conteúdos ou temas trabalhados pelos professores.",
            "Os professores demonstraram domínio dos conteúdos abordados nas disciplinas.",
            "As atividades acadêmicas desenvolvidas dentro e fora da sala de aula possibilitaram reflexão, convivência e respeito à diversidade.",
        ]
        infra_questions_text = [
            "O estágio supervisionado proporcionou experiências diversificadas para a sua formação.",
            "Os estudantes participaram de avaliações periódicas do curso (disciplinas, atuação dos professores, infraestrutura).",
            "Os professores apresentaram disponibilidade para atender os estudantes fora do horário das aulas.",
            "Os professores utilizaram tecnologias da informação e comunicação (TICs) como estratégia de ensino (projetor multimídia, laboratório de informática, ambiente virtual de aprendizagem).",
            "A instituição dispôs de quantidade suficiente de funcionários para o apoio administrativo e acadêmico.",
            "O curso disponibilizou monitores ou tutores para auxiliar os estudantes.",
            "As condições de infraestrutura das salas de aula foram adequadas.",
            "Os equipamentos e materiais disponíveis para as aulas práticas foram adequados para a quantidade de estudantes.",
            "Os ambientes e equipamentos destinados às aulas práticas foram adequados ao curso.",
            "A biblioteca dispôs das referências bibliográficas que os estudantes necessitaram.",
            "A instituição contou com biblioteca virtual ou conferiu acesso a obras disponíveis em acervos virtuais.",
            "A instituição promoveu atividades de cultura, de lazer e de interação social.",
            "A instituição dispôs de refeitório, cantina e banheiros em condições adequadas que atenderam as necessidades dos seus usuários.",
        ]
        oaf_questions_text = [
            "Foram oferecidas oportunidades para os estudantes participarem de programas, projetos ou atividades de extensão universitária.",
            "Foram oferecidas oportunidades para os estudantes participarem de projetos de iniciação científica e de atividades que estimularam a investigação acadêmica.",
            "O curso ofereceu condições para os estudantes participarem de eventos internos e/ou externos à instituição.",
            "A instituição ofereceu oportunidades para os estudantes atuarem como representantes em órgãos colegiados.",
            "Foram oferecidas oportunidades para os estudantes realizarem intercâmbios e/ou estágios no país.",
            "Foram oferecidas oportunidades para os estudantes realizarem intercâmbios e/ou estágios fora do país.",
        ]

        odp_questions = [
            "QE_I27", "QE_I28", "QE_I29", "QE_I30", "QE_I31", "QE_I32", "QE_I33", "QE_I34",
            "QE_I35", "QE_I36", "QE_I37", "QE_I38", "QE_I39", "QE_I40", "QE_I42", "QE_I47",
            "QE_I48", "QE_I49", "QE_I51", "QE_I55", "QE_I57", "QE_I66",
        ]
        infra_questions = [
            "QE_I50", "QE_I54", "QE_I56", "QE_I58", "QE_I59", "QE_I60", "QE_I61",
            "QE_I62", "QE_I63", "QE_I64", "QE_I65", "QE_I67", "QE_I68",
        ]
        oaf_questions = ["QE_I43", "QE_I44", "QE_I45", "QE_I46", "QE_I52", "QE_I53"]

        # ---------------------------------------------------------
        # Resolve course_code
        # ---------------------------------------------------------
        course_code = None
        for code, details in COURSE_CODES.items():
            if details[1] == st.session_state["curso_op_qe"] and details[3] == st.session_state["municipio_op_qe"]:
                course_code = code
                break

        if course_code:
            with st.spinner("Gerando gráficos do questionário..."):
                # Médias
                _, odp_img_av = plot_average_graph(QE_filtrado, course_code, odp_questions, odp_questions_text)
                _, infra_img_av = plot_average_graph(QE_filtrado, course_code, infra_questions, infra_questions_text)
                _, oaf_img_av = plot_average_graph(QE_filtrado, course_code, oaf_questions, oaf_questions_text)

                # Contagens
                _, odp_img_co = plot_count_graph(QE_filtrado, course_code, odp_questions)
                _, infra_img_co = plot_count_graph(QE_filtrado, course_code, infra_questions)
                _, oaf_img_co = plot_count_graph(QE_filtrado, course_code, oaf_questions)

                # session_state (PDF)
                st.session_state["odp_img_av"] = odp_img_av
                st.session_state["infra_img_av"] = infra_img_av
                st.session_state["oaf_img_av"] = oaf_img_av
                st.session_state["odp_img_co"] = odp_img_co
                st.session_state["infra_img_co"] = infra_img_co
                st.session_state["oaf_img_co"] = oaf_img_co

                # Render lado a lado
                with tab1:
                    col_avg_1, col_count_1 = st.columns(2)
                    with col_avg_1:
                        st.image(
                            odp_img_av,
                            use_container_width=True,
                            caption="Gráfico de Médias - Organização Didático-Pedagógica",
                        )
                    with col_count_1:
                        st.image(
                            odp_img_co,
                            use_container_width=True,
                            caption="Gráfico de Contagem - Organização Didático-Pedagógica",
                        )

                with tab2:
                    col_avg_2, col_count_2 = st.columns(2)
                    with col_avg_2:
                        st.image(
                            infra_img_av,
                            use_container_width=True,
                            caption="Gráfico de Médias - Infraestrutura",
                        )
                    with col_count_2:
                        st.image(
                            infra_img_co,
                            use_container_width=True,
                            caption="Gráfico de Contagem - Infraestrutura",
                        )

                with tab3:
                    col_avg_3, col_count_3 = st.columns(2)
                    with col_avg_3:
                        st.image(
                            oaf_img_av,
                            use_container_width=True,
                            caption="Gráfico de Médias - Ampliação da Formação",
                        )
                    with col_count_3:
                        st.image(
                            oaf_img_co,
                            use_container_width=True,
                            caption="Gráfico de Contagem - Ampliação da Formação",
                        )
        else:
            st.warning("Não foi possível encontrar os detalhes para o curso selecionado.")

        # ---------------------------------------------------------
        # PDF (apenas 2023)
        # ---------------------------------------------------------
        with tab4:
            st.subheader("Questionário do Estudante - ENADE 2023")
            pdf_name = "anexo_qe_2023.pdf"

            try:
                with open(pdf_name, "rb") as f:
                    pdf_bytes = f.read()
                    pdf_viewer(input=pdf_bytes, width=800)
            except FileNotFoundError:
                st.error(f"Arquivo '{pdf_name}' não encontrado na pasta principal do projeto.")