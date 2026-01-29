# paginas/questionario_do_estudante_2025.py
# ESPECÍFICO PARA ENAMED 2025 (Medicina)
# AJUSTADO: Correção do nome da IES (569 -> UFPA) usando hei_dict e filtros corretos.

import streamlit as st
import pandas as pd
from streamlit_pdf_viewer import pdf_viewer

from utils import atualiza_cursos
from analysis import plot_average_graph, plot_count_graph

# --- HELPERS DE FORMATAÇÃO (Iguais ao enamed.py) ---
def _norm_city(x: str) -> str:
    """Normaliza município para comparação (remove acentos e lowercase)."""
    if x is None:
        return ""
    s = str(x).strip().lower()
    return (s.replace("á", "a").replace("à", "a").replace("ã", "a").replace("â", "a")
            .replace("é", "e").replace("ê", "e").replace("í", "i")
            .replace("ó", "o").replace("ô", "o").replace("õ", "o")
            .replace("ú", "u").replace("ç", "c"))

def _co_ies_to_int(co_ies):
    if pd.isna(co_ies):
        return None
    try:
        return int(float(co_ies))
    except Exception:
        return co_ies

def _ies_label(co_ies, hei_dict: dict) -> str:
    """Transforma o código 569 em 'Universidade Federal do Pará...'"""
    c = _co_ies_to_int(co_ies)
    if c is None:
        return "IES desconhecida"
    # Tenta pegar o nome no dicionário, se não achar, mostra o código formatado
    nome = hei_dict.get(c)
    if nome:
        return f"{nome} ({c})"
    return str(c)

# --- FUNÇÃO PRINCIPAL (Agora recebe hei_dict) ---
def show_page(QE_data, UFPA_data, COURSE_CODES, hei_dict):
    with st.container():
        st.markdown(
            """
        <div class="text-container">
            <h1>Questionário do Estudante - ENAMED 2025</h1>
            <p>
                Esta seção apresenta a percepção dos estudantes de Medicina sobre o curso. 
                As questões variam de 1 (discordância total) a 6 (concordância total), exceto as questões de recomendação (NPS) que são de 0 a 10.
            </p>
            <p>
                Os gráficos abaixo estão organizados por dimensões estratégicas: <strong>Destaques</strong>, 
                <strong>Organização Didático-Pedagógica</strong>, <strong>Infraestrutura</strong> e <strong>Ampliação da Formação</strong>.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ---------------------------------------------------------
        # PREPARAÇÃO DOS DADOS (TRAVADO EM 2025)
        # ---------------------------------------------------------
        edicao_atual = "2025"

        # Filtra Dataframes para 2025 internamente
        if "EDICAO" in QE_data.columns:
            QE_filtrado = QE_data[QE_data["EDICAO"].astype(str) == edicao_atual].copy()
        elif "NU_ANO" in QE_data.columns:
            QE_filtrado = QE_data[QE_data["NU_ANO"].astype(str) == edicao_atual].copy()
        else:
            QE_filtrado = QE_data.copy()

        if "EDICAO" in UFPA_data.columns:
            UFPA_filtrado = UFPA_data[UFPA_data["EDICAO"].astype(str) == edicao_atual].copy()
        elif "NU_ANO" in UFPA_data.columns:
            UFPA_filtrado = UFPA_data[UFPA_data["NU_ANO"].astype(str) == edicao_atual].copy()
        else:
            UFPA_filtrado = UFPA_data.copy()

        if UFPA_filtrado.empty:
            st.warning("Não há dados carregados para a edição de 2025.")
            return

        # ---------------------------------------------------------
        # CONTROLES DE FILTRO (MUNICÍPIO -> IES -> CURSO)
        # ---------------------------------------------------------
        
        # Toggle para expandir municípios
        mostrar_todos_mun = st.toggle("Mostrar todos os municípios", value=False)
        
        # 1. Lista de Municípios
        municipios_raw = sorted(UFPA_filtrado["NOME_MUNIC_CURSO"].dropna().unique().tolist())
        
        if not mostrar_todos_mun:
            alvos = ["belem", "altamira"]
            municipios = [m for m in municipios_raw if _norm_city(m) in alvos]
        else:
            municipios = municipios_raw

        if not municipios:
            st.warning("Nenhum município encontrado.")
            return

        # Session State
        if "municipio_op_qe_25" not in st.session_state or st.session_state["municipio_op_qe_25"] not in municipios:
            st.session_state["municipio_op_qe_25"] = municipios[0]

        def on_change_mun():
            st.session_state.pop("ies_label_qe_25", None)
            st.session_state.pop("curso_op_qe_25", None)

        def on_change_ies():
            st.session_state.pop("curso_op_qe_25", None)

        col_mun, col_ies, col_cur = st.columns(3)

        # --- Coluna 1: Município ---
        with col_mun:
            municipio_sel = st.selectbox(
                "Selecione o Município",
                municipios,
                key="municipio_op_qe_25",
                on_change=on_change_mun
            )

        # Filtra DF pelo município
        df_mun = UFPA_filtrado[UFPA_filtrado["NOME_MUNIC_CURSO"] == municipio_sel]

        # --- Coluna 2: IES (CORRIGIDO COM HEI_DICT) ---
        # Pega os códigos únicos disponíveis neste município
        ies_codes = df_mun["CO_IES"].dropna().unique().tolist()

        if not ies_codes:
            st.warning("Nenhuma IES encontrada.")
            return

        # Cria labels bonitos usando o dicionário
        ies_labels = sorted([_ies_label(c, hei_dict) for c in ies_codes])
        # Cria mapa reverso: "Nome (Código)" -> Código
        label_to_ies = {_ies_label(c, hei_dict): c for c in ies_codes}

        if "ies_label_qe_25" not in st.session_state or st.session_state["ies_label_qe_25"] not in ies_labels:
            st.session_state["ies_label_qe_25"] = ies_labels[0]

        with col_ies:
            ies_label_sel = st.selectbox(
                "Selecione a Faculdade (IES)",
                ies_labels,
                key="ies_label_qe_25",
                on_change=on_change_ies
            )
        
        # Recupera o código real para filtrar o dataframe
        ies_selected_code = label_to_ies[ies_label_sel]
        
        # Filtra DF pela IES (usando o código)
        # Convertemos para float/int/str para garantir compatibilidade
        try:
             df_ies = df_mun[df_mun["CO_IES"].astype(float) == float(ies_selected_code)]
        except:
             df_ies = df_mun[df_mun["CO_IES"].astype(str) == str(ies_selected_code)]

        # --- Coluna 3: Curso ---
        cursos_list = sorted(df_ies["NOME_CURSO"].dropna().unique().tolist())

        if not cursos_list:
            st.warning("Nenhum curso encontrado.")
            return
            
        if "curso_op_qe_25" not in st.session_state or st.session_state["curso_op_qe_25"] not in cursos_list:
            st.session_state["curso_op_qe_25"] = cursos_list[0]

        with col_cur:
            curso_sel = st.selectbox(
                "Selecione o Curso",
                cursos_list,
                key="curso_op_qe_25"
            )

        # ---------------------------------------------------------
        # DEFINIÇÃO DAS QUESTÕES
        # ---------------------------------------------------------
        QUESTIONS_DB = {
            "QE_I18": "Foram oferecidas oportunidades para os estudantes participarem de programas, projetos ou atividades de extensão universitária.",
            "QE_I19": "Foram oferecidas oportunidades para os estudantes participarem de projetos de iniciação científica e/ou de atividades que estimularam a investigação acadêmica.",
            "QE_I20": "As atividades realizadas durante seu trabalho de conclusão de curso contribuíram para qualificar sua formação profissional.",
            "QE_I21": "As relações professor-aluno ao longo do curso foram positivas, estimulando os estudantes a estudar e aprender.",
            "QE_I22": "Os professores apresentaram e discutiram os planos de ensino/curso das disciplinas com os estudantes.",
            "QE_I23": "As referências bibliográficas indicadas pelos professores contribuíram para seus estudos e aprendizagens.",
            "QE_I24": "As avaliações da aprendizagem realizadas durante o curso foram compatíveis com os conteúdos ou temas trabalhados pelos professores.",
            "QE_I25": "Os professores demonstraram domínio dos conteúdos abordados nas disciplinas.",
            "QE_I26": "Os professores utilizaram estratégias e instrumentos de avaliação diversificados (provas, seminários, trabalhos em grupo, portfólio, autoavaliação etc.).",
            "QE_I27": "Os professores ofereceram devolutivas das avaliações (comentários, explicações, sugestões para melhoria) que auxiliaram os estudantes a avançar em suas aprendizagens.",
            "QE_I28": "Os professores estimularam a participação ativa dos estudantes durante as aulas (por meio de atividades em grupo, discussões, seminários etc.) não se limitando às aulas expositivas.",
            "QE_I29": "O curso disponibilizou quantidade suficiente de professores e preceptores para auxiliar os estudantes.",
            "QE_I30": "As atividades práticas de ensino contemplaram a quantidade adequada de equipamentos em relação aos estudantes.",
            "QE_I31": "Foram oferecidas oportunidades para os estudantes superarem dificuldades relacionadas ao processo de formação.",
            "QE_I32": "A coordenação do curso esteve disponível para orientação acadêmica dos estudantes.",
            "QE_I33": "O curso favoreceu a articulação do conhecimento teórico com atividades práticas.",
            "QE_I34": "O curso propiciou acesso a conhecimentos atualizados e/ou contemporâneos em sua área de formação.",
            "QE_I35": "As disciplinas cursadas contribuíram para sua formação como profissional.",
            "QE_I36": "As metodologias de ensino utilizadas no curso desafiaram você a se posicionar mais criticamente diante do conhecimento.",
            "QE_I37": "Os estudantes participaram de avaliações periódicas das condições de formação (disciplinas, atuação dos professores, infraestrutura).",
            "QE_I38": "O curso proporcionou condições de acesso adequado às bibliografias indicadas nas disciplinas, de forma física ou virtual.",
            "QE_I39": "As salas de aula apresentaram tamanho, mobiliário e recursos tecnológicos adequados.",
            "QE_I40": "Os ambientes e equipamentos destinados às aulas práticas foram adequados ao curso e à quantidade de estudantes.",
            "QE_I41": "Os laboratórios de habilidades e simulação de atividade assistencial permitiram a capacitação dos estudantes nas diversas competências desenvolvidas.",
            "QE_I42": "Foram realizadas simulações de alta fidelidade em diferentes etapas do curso.",
            "QE_I43": "A integração do curso com o sistema de saúde viabilizou a formação do estudante em serviço, conforme necessidades locais e regionais.",
            "QE_I44": "No meu curso, aprendi a integrar conhecimentos básicos e clínicos na atenção integral à saúde, considerando os princípios do SUS.",
            "QE_I45": "No meu curso, aprendi a realizar o cuidado em saúde com base em práticas éticas, humanizadas e orientadas para a promoção da saúde.",
            "QE_I46": "No meu curso, aprendi a utilizar evidências científicas para fundamentar a tomada de decisão clínica e terapêutica.",
            "QE_I47": "Vivenciei a formação a partir de metodologias ativas, como aprendizagem baseada em problemas (PBL) e simulação.",
            "QE_I48": "Pratiquei medicina por meio de estágios supervisionados em diferentes níveis de atenção (primária, secundária e terciária) na rede pública.",
            "QE_I49": "Pratiquei medicina por meio de estágios supervisionados em diferentes níveis de atenção na rede privada.",
            "QE_I50": "No meu curso, aprendi a estabelecer comunicação efetiva com usuários, familiares e equipes.",
            "QE_I51": "No meu curso, aprendi a atuar em equipes multiprofissionais de saúde de forma colaborativa.",
            "QE_I52": "No meu curso, aprendi a utilizar recursos tecnológicos e de informação em saúde de maneira crítica.",
            "QE_I53": "No meu curso, aprendi a desenvolver habilidades de liderança e gestão de processos de trabalho.",
            "QE_I54": "No meu curso, aprendi a refletir continuamente sobre a minha formação (aprendizagem permanente).",
            "QE_I55": "No meu curso, aprendi a relacionar as atividades práticas de ensino ao contexto de saúde local e regional.",
            "QE_I56": "No meu curso, aprendi a desenvolver competências práticas relacionadas a ações de atenção à saúde e bem-estar social.",
            "QE_I57": "Em uma escala de 0 a 10, o quanto você recomendaria o seu curso para um amigo ou colega?",
            "QE_I58": "Em uma escala de 0 a 10, o quanto você recomendaria a sua Instituição de Educação Superior para um amigo ou colega?"
        }

        # ---------------------------------------------------------
        # SANEAMENTO DE DADOS
        # ---------------------------------------------------------
        cols_questoes = list(QUESTIONS_DB.keys())
        cols_existentes = [c for c in cols_questoes if c in QE_filtrado.columns]
        
        if cols_existentes:
            QE_filtrado[cols_existentes] = QE_filtrado[cols_existentes].apply(pd.to_numeric, errors='coerce')

        # ---------------------------------------------------------
        # AGRUPAMENTOS
        # ---------------------------------------------------------
        ids_nps = ["QE_I57", "QE_I58"]
        ids_tech = ["QE_I40", "QE_I41", "QE_I42"]
        ids_metodologia = ["QE_I47", "QE_I33", "QE_I36"]
        ids_rede = ["QE_I43", "QE_I48", "QE_I49"]
        ids_infra = ["QE_I29", "QE_I30", "QE_I38", "QE_I39", "QE_I40", "QE_I41", "QE_I42"]
        ids_oaf = ["QE_I18", "QE_I19"]
        exclude_set = set(ids_infra + ids_oaf + ids_nps)
        ids_odp = [k for k in QUESTIONS_DB.keys() if k not in exclude_set]

        # ---------------------------------------------------------
        # TABS E RENDERIZAÇÃO
        # ---------------------------------------------------------
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🚀 Destaques Estratégicos",
            "📚 Didático-Pedagógica",
            "🏢 Infraestrutura",
            "🌍 Ampliação da Formação",
            "📄 Visualizar PDF"
        ])

        # Resolve código do curso
        course_code = None
        for code, details in COURSE_CODES.items():
            # details: [group_code, nome_curso, modality, municipio]
            if details[1] == curso_sel and details[3] == municipio_sel:
                # Opcional: Validar se a IES bate (se você tiver a info da IES no course_codes)
                # Como não temos, confiamos no par Curso+Município
                course_code = code
                break

        if course_code:
            
            # --- TAB 1: DESTAQUES ---
            with tab1:
                st.info("Indicadores chave de desempenho e diferenciais competitivos (Tecnologia, Metodologias e Satisfação).")
                st.subheader("Satisfação Geral (Escala 0-10)")
                _, img_nps = plot_average_graph(QE_filtrado, course_code, ids_nps, [QUESTIONS_DB[k] for k in ids_nps])
                st.image(img_nps, use_container_width=True)

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.subheader("Infraestrutura de Alta Complexidade")
                    _, img_tech = plot_average_graph(QE_filtrado, course_code, ids_tech, [QUESTIONS_DB[k] for k in ids_tech])
                    st.image(img_tech, use_container_width=True, caption="Simulação e Laboratórios")
                with col_d2:
                    st.subheader("Modelo Pedagógico (PBL)")
                    _, img_met = plot_average_graph(QE_filtrado, course_code, ids_metodologia, [QUESTIONS_DB[k] for k in ids_metodologia])
                    st.image(img_met, use_container_width=True, caption="Metodologias Ativas e Críticas")

                st.subheader("Inserção na Rede de Saúde")
                _, img_rede = plot_average_graph(QE_filtrado, course_code, ids_rede, [QUESTIONS_DB[k] for k in ids_rede])
                st.image(img_rede, use_container_width=True, caption="Integração Ensino-Serviço (SUS)")

            # --- TAB 2: DIDÁTICO-PEDAGÓGICA ---
            with tab2:
                col_avg_odp, col_count_odp = st.columns(2)
                _, img_av_odp = plot_average_graph(QE_filtrado, course_code, ids_odp, [QUESTIONS_DB[k] for k in ids_odp])
                _, img_co_odp = plot_count_graph(QE_filtrado, course_code, ids_odp)
                with col_avg_odp: st.image(img_av_odp, use_container_width=True, caption="Médias - ODP")
                with col_count_odp: st.image(img_co_odp, use_container_width=True, caption="Contagem - ODP")

            # --- TAB 3: INFRAESTRUTURA ---
            with tab3:
                col_avg_inf, col_count_inf = st.columns(2)
                _, img_av_inf = plot_average_graph(QE_filtrado, course_code, ids_infra, [QUESTIONS_DB[k] for k in ids_infra])
                _, img_co_inf = plot_count_graph(QE_filtrado, course_code, ids_infra)
                with col_avg_inf: st.image(img_av_inf, use_container_width=True, caption="Médias - Infraestrutura")
                with col_count_inf: st.image(img_co_inf, use_container_width=True, caption="Contagem - Infraestrutura")

            # --- TAB 4: AMPLIAÇÃO DA FORMAÇÃO ---
            with tab4:
                col_avg_oaf, col_count_oaf = st.columns(2)
                _, img_av_oaf = plot_average_graph(QE_filtrado, course_code, ids_oaf, [QUESTIONS_DB[k] for k in ids_oaf])
                _, img_co_oaf = plot_count_graph(QE_filtrado, course_code, ids_oaf)
                with col_avg_oaf: st.image(img_av_oaf, use_container_width=True, caption="Médias - Ampliação da Formação")
                with col_count_oaf: st.image(img_co_oaf, use_container_width=True, caption="Contagem - Ampliação da Formação")

        else:
            st.error("Curso não encontrado para os filtros selecionados.")

        # --- TAB 5: PDF ---
        with tab5:
            st.subheader("Questionário do Estudante - ENAMED 2025")
            pdf_name = "anexo_qe_2025.pdf" 
            try:
                with open(pdf_name, "rb") as f:
                    pdf_bytes = f.read()
                    pdf_viewer(input=pdf_bytes, width=800)
            except FileNotFoundError:
                st.error(f"Arquivo '{pdf_name}' não encontrado na pasta do projeto.")