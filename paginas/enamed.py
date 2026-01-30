# paginas/enamed.py
# ENAMED 2025 – Desempenho Geral + Percepção de Prova + Item Analysis
# (ATUALIZADO: Ajuste visual no gráfico de barras - Limite Y aumentado e sufixo %)
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from streamlit_pdf_viewer import pdf_viewer

_FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

# ============================================================
# Helpers
# ============================================================
def to_numeric_robust(series: pd.Series) -> pd.Series:
    """Converte Series pra float de forma robusta."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    s = series.copy()
    s = s.fillna("").map(str).str.strip()
    s = s.str.replace(",", ".", regex=False)
    
    def parse_cell(x: str) -> float:
        if x == "" or x == ".":
            return np.nan
        try:
            return float(x)
        except Exception:
            nums = _FLOAT_RE.findall(x)
            if not nums:
                return np.nan
            vals = []
            for n in nums:
                try:
                    vals.append(float(n))
                except Exception:
                    continue
            return float(np.mean(vals)) if vals else np.nan
            
    return s.apply(parse_cell)

def _norm_city(x: str) -> str:
    """Normaliza município pra comparar."""
    if x is None:
        return ""
    s = str(x).strip().lower()
    return (s.replace("á", "a").replace("à", "a").replace("ã", "a").replace("â", "a")
            .replace("é", "e").replace("ê", "e")
            .replace("í", "i")
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
    """Label amigável pra IES."""
    c = _co_ies_to_int(co_ies)
    if c is None:
        return "IES desconhecida"
    nome = hei_dict.get(c)
    if nome:
        return f"{nome} (CO_IES={c})"
    return f"CO_IES={c}"

# ============================================================
# Página Principal
# ============================================================
def show_page(Enade, UFPA_data, COURSE_CODES, hei_dict):
    st.markdown(
        """
        <div class="text-container">
            <h1>ENAMED 2025 – Desempenho e Percepção</h1>
            <p>
                Esta seção apresenta análises do desempenho dos estudantes, incluindo a análise detalhada de acertos por questão
                e a percepção sobre a prova aplicada.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # Filtra somente 2025
    # ---------------------------------------------------------
    if "EDICAO" not in Enade.columns:
        st.error("A coluna EDICAO não existe no DataFrame Enade.")
        return

    df_2025 = Enade[Enade["EDICAO"] == "2025"].copy()

    if df_2025.empty:
        st.warning("Não há dados disponíveis do ENAMED 2025.")
        return

    # ---------------------------------------------------------
    # Controles de filtro
    # ---------------------------------------------------------
    mostrar_todos_municipios = st.toggle(
        "Mostrar todos os municípios",
        value=False,
        help="Por padrão, mostra apenas Belém e Altamira.",
    )

    municipios_all = (
        df_2025.loc[df_2025["CO_IES"].notna(), "NOME_MUNIC_CURSO"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if not mostrar_todos_municipios:
        allowed = {"belem", "altamira"}
        municipios_filtrados = [m for m in municipios_all if _norm_city(m) in allowed]
    else:
        municipios_filtrados = municipios_all

    municipios = sorted(municipios_filtrados)

    if not municipios:
        st.warning("Não foi possível listar municípios.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        municipio = st.selectbox("Selecione o Município", municipios)

    df_mun = df_2025[df_2025["NOME_MUNIC_CURSO"] == municipio].copy()

    if df_mun.empty:
        st.warning("Não há dados para o município selecionado.")
        return

    # Filtro IES
    ies_codes = df_mun["CO_IES"].dropna().unique().tolist()
    if not ies_codes:
        st.warning("Não há CO_IES disponíveis.")
        return

    ies_labels = sorted([_ies_label(c, hei_dict) for c in ies_codes])
    label_to_ies = {_ies_label(c, hei_dict): c for c in ies_codes}

    with col2:
        ies_label_selected = st.selectbox("Selecione a Faculdade (IES)", ies_labels)

    ies_selected = label_to_ies[ies_label_selected]
    df_mun_ies = df_mun[df_mun["CO_IES"] == ies_selected].copy()

    if df_mun_ies.empty:
        st.warning("Sem dados para a IES selecionada.")
        return

    # Filtro Curso
    cursos = sorted(df_mun_ies["NOME_CURSO"].dropna().unique().tolist())
    if not cursos:
        st.warning("Sem cursos disponíveis.")
        return

    with col3:
        curso = st.selectbox("Selecione o Curso", cursos)

    curso_df = df_mun_ies[df_mun_ies["NOME_CURSO"] == curso].copy()

    if curso_df.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    # ---------------------------------------------------------
    # Saneamento numérico das Médias
    # ---------------------------------------------------------
    cols_media = [
        "QT_ACERTO_AREA_1", "QT_ACERTO_AREA_2", "QT_ACERTO_AREA_3",
        "QT_ACERTO_AREA_4", "QT_ACERTO_AREA_5",
    ]
    for c in cols_media:
        if c in curso_df.columns:
            curso_df[c] = to_numeric_robust(curso_df[c])

    if "PER_ACERTO_ENARE" in curso_df.columns:
        curso_df["PER_ACERTO_ENARE"] = to_numeric_robust(curso_df["PER_ACERTO_ENARE"])

    if "PROFICIENCIA" in curso_df.columns:
        curso_df["PROFICIENCIA_NUM"] = to_numeric_robust(curso_df["PROFICIENCIA"])

    # ---------------------------------------------------------
    # Definição das Abas
    # ---------------------------------------------------------
    tab_acertos, tab_medias, tab_area, tab_prof, tab_enare, tab_percepcao, tab_pdf = st.tabs([
        "✅ Percentual de Acertos",
        "📊 Médias Gerais",
        "📈 Distribuição por Área",
        "🎓 Proficiência",
        "🧮 ENARE",
        "📝 Percepção de Prova",
        "📄 PDF Percepção"
    ])

    # =========================
    # TAB 1) MÉDIAS GERAIS
    # =========================
    with tab_medias:
        cols_media_exist = [c for c in cols_media if c in curso_df.columns]
        if not cols_media_exist:
            st.info("As colunas QT_ACERTO_AREA_* não estão disponíveis.")
        else:
            medias = curso_df[cols_media_exist].mean(numeric_only=True)
            label_map = {
                "QT_ACERTO_AREA_1": "Clínica Médica",
                "QT_ACERTO_AREA_2": "Cirurgia Geral",
                "QT_ACERTO_AREA_3": "Pediatria",
                "QT_ACERTO_AREA_4": "Ginecologia e Obstetrícia",
                "QT_ACERTO_AREA_5": "Medicina da Família e Comunidade",
            }
            df_medias = (
                medias.rename(index=label_map)
                .rename("Média de Acertos (/20)")
                .to_frame()
                .reset_index()
                .rename(columns={"index": "Área de Conhecimento"})
            )
            
            # --- CÁLCULO DE PERCENTUAL ---
            df_medias["Percentual de Acerto"] = (df_medias["Média de Acertos (/20)"] / 20) * 100
            
            # Formatação
            df_medias["Média de Acertos (/20)"] = df_medias["Média de Acertos (/20)"].map(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            )
            df_medias["Percentual de Acerto"] = df_medias["Percentual de Acerto"].map(
                lambda x: f"{x:.1f}%" if pd.notna(x) else ""
            )
            
            df_medias.index = range(1, len(df_medias) + 1)
            st.dataframe(df_medias, use_container_width=True)

    # =========================
    # TAB 2) DISTRIBUIÇÃO POR ÁREA
    # =========================
    with tab_area:
        import textwrap
        cols_media_exist = [c for c in cols_media if c in curso_df.columns]
        if not cols_media_exist:
            st.info("As colunas QT_ACERTO_AREA_* não estão disponíveis.")
        else:
            medias = curso_df[cols_media_exist].mean(numeric_only=True)
            NOME_AREAS = {
                "QT_ACERTO_AREA_1": "Cirurgia Geral",
                "QT_ACERTO_AREA_2": "Clínica Médica",
                "QT_ACERTO_AREA_3": "Pediatria",
                "QT_ACERTO_AREA_4": "Ginecologia e Obstetrícia",
                "QT_ACERTO_AREA_5": "Medicina da Família e Comunidade"
            }
            raw_labels = [NOME_AREAS.get(c, c) for c in cols_media_exist]
            labels_quebrados = [textwrap.fill(text, width=12) for text in raw_labels]
            values = [float(medias[c]) if pd.notna(medias[c]) else 0.0 for c in cols_media_exist]

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(labels_quebrados, values, color="#2E5C8A")
            ax.set_ylabel("Média de Acertos (Max: 20)")
            ax.set_title("Desempenho por Área – ENAMED 2025")
            ax.bar_label(bars, fmt="%.2f", padding=3)
            
            if values:
                ax.set_ylim(0, max(values) * 1.25) 
                
            plt.xticks(rotation=0)
            plt.tight_layout()
            st.pyplot(fig)

    # =========================
    # TAB 3) PROFICIÊNCIA
    # =========================
    with tab_prof:
        if "PROFICIENCIA_NUM" not in curso_df.columns:
            st.info("A coluna PROFICIENCIA não está disponível.")
        else:
            prof = curso_df["PROFICIENCIA_NUM"]
            n_ok = int(prof.notna().sum())
            if n_ok == 0:
                st.warning("Sem dados válidos de proficiência.")
            else:
                prof_series = prof.dropna()
                prof_mean = float(prof_series.mean())
                CORTE_OFICIAL_INEP = -0.41 # Exemplo
                aprovados = prof_series[prof_series >= CORTE_OFICIAL_INEP].count()
                taxa_aprovacao = (aprovados / len(prof_series)) * 100

                st.markdown(
                    """
                    <style>
                    [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; text-align: center; }
                    [data-testid="stMetricLabel"] { justify-content: center; color: #000000 !important; width: 100%; }
                    [data-testid="stMetricValue"] { color: #000000 !important; }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Nota Média (Z-Score)", f"{prof_mean:.2f}")
                col_m2.metric("Nota de Corte", f"{CORTE_OFICIAL_INEP:.2f}")
                col_m3.metric("Taxa de Proficiência", f"{taxa_aprovacao:.1f}%")

                fig, ax = plt.subplots(figsize=(8, 5))
                ax.hist(prof_series, bins=20, color="#1C6C0F", alpha=0.7, label='Alunos')
                ax.axvline(prof_mean, color='blue', linestyle="--", linewidth=2, label=f'Média Turma ({prof_mean:.2f})')
                ax.set_xlabel("Proficiência (Escala Padronizada)")
                ax.set_ylabel("Número de Estudantes")
                ax.set_title("Distribuição da Proficiência – ENAMED 2025")

                x_min = min(prof_series.min(), -3.0)
                x_max = max(prof_series.max(), 3.0)
                ax.set_xlim(left=x_min, right=x_max)
                ax.legend(loc='upper right')
                plt.tight_layout()
                st.pyplot(fig)
            st.caption(f"Proficiência baseada em {n_ok} notas válidas.")

    # =========================
    # TAB 4) ENARE
    # =========================
    with tab_enare:
        if "PER_ACERTO_ENARE" not in curso_df.columns:
            st.info("A coluna PER_ACERTO_ENARE não está disponível.")
        else:
            enare = curso_df["PER_ACERTO_ENARE"]
            n_total = len(enare)
            n_ok = int(enare.notna().sum())
            if n_ok == 0:
                st.warning("Sem dados válidos para o ENARE.")
            else:
                enare_mean = float(enare.mean(skipna=True))
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.hist(enare.dropna(), bins=20, color="#2E5C8A")
                ax.set_xlabel("Percentual de Acerto (ENARE)")
                ax.set_ylabel("Número de Estudantes")
                ax.set_title("Distribuição do Percentual de Acerto – ENARE")
                ax.axvline(enare_mean, linestyle="--", linewidth=2)
                ax.text(
                    0.98, 0.98, f"Média: {enare_mean:.2f}%",
                    transform=ax.transAxes, ha="right", va="top", fontsize=11,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85, ec="0.7"),
                )
                plt.tight_layout()
                st.pyplot(fig)
            st.caption(f"ENARE: {n_ok}/{n_total} valores válidos.")

    # =========================
    # TAB 5) PERCENTUAL DE ACERTOS (ATUALIZADO)
    # =========================
    with tab_acertos:
        st.subheader("Análise Detalhada por Questão")
        
        candidatos_prioridade = ["DS_VT_ACE_OCE", "DS_VT_ACE_OBJ", "DS_VT_ACE_OFG"]
        candidatos_genericos = [c for c in curso_df.columns if "DS_VT_ACE" in c]
        
        col_vetor = None
        
        todos_candidatos = []
        for c in candidatos_prioridade:
            if c not in todos_candidatos: 
                todos_candidatos.append(c)
        for c in candidatos_genericos:
            if c not in todos_candidatos: 
                todos_candidatos.append(c)
        
        for c in todos_candidatos:
            if c in curso_df.columns:
                temp_series = curso_df[c].astype(str).str.strip()
                validos = temp_series[temp_series != ""].count()
                validos_nan = curso_df[c].notna().sum()
                if validos > 0 and validos_nan > 0:
                    col_vetor = c
                    break
        
        if col_vetor is None:
            st.error("Não foi possível encontrar uma coluna válida com o vetor de respostas (ex: DS_VT_ACE_OCE).")
            st.info(f"Colunas disponíveis no dataset: {list(curso_df.columns)}")
        else:
            
            raw_data = curso_df[col_vetor].astype(str).replace("nan", np.nan)
            vetores = raw_data[raw_data.str.strip() != ""].dropna()
            
            if vetores.empty:
                st.warning(f"A coluna {col_vetor} existe, mas não contém dados válidos para os filtros selecionados.")
            else:
                tamanhos = vetores.str.len()
                qtd_questoes = int(tamanhos.mode()[0]) if not tamanhos.empty else 0
                
                if qtd_questoes == 0:
                     st.warning("Vetor de respostas com comprimento zero.")
                else:
                    acertos_por_questao = [0] * qtd_questoes
                    total_alunos_vetor = 0
                    
                    for v in vetores:
                        v = v.strip() 
                        if len(v) < qtd_questoes:
                            continue 
                        
                        total_alunos_vetor += 1
                        
                        for i in range(qtd_questoes):
                            if v[i] == '1': 
                                acertos_por_questao[i] += 1
                    
                    if total_alunos_vetor == 0:
                         st.warning("Nenhum vetor válido encontrado após processamento.")
                    else:
                        labels_q = [f"Q{i+1}" for i in range(qtd_questoes)]
                        percentuais = [(x / total_alunos_vetor) * 100 for x in acertos_por_questao]
                        
                        fig, ax = plt.subplots(figsize=(12, 5)) 
                        bars = ax.bar(labels_q, percentuais, color="#2E5C8A")
                        
                        ax.set_ylabel("% de Acertos")
                        ax.set_xlabel("Questão")
                        ax.set_title(f"Percentual de Acertos por Questão \n(Total de alunos: {total_alunos_vetor})")
                        
                        # --- MODIFICAÇÃO: Margem superior aumentada para 115 ---
                        ax.set_ylim(0, 115)
                        
                        # --- MODIFICAÇÃO: Adicionado '%%' no formato para aparecer o símbolo % ---
                        ax.bar_label(bars, fmt="%.0f%%", padding=3, fontsize=7, rotation=90)
                        
                        plt.xticks(rotation=90, fontsize=8)
                        plt.tight_layout()
                        
                        st.pyplot(fig)

    # =========================
    # TAB 6) PERCEPÇÃO DE PROVA
    # =========================
    with tab_percepcao:
        st.subheader("Questionário de Percepção sobre a Prova")
        
        PERCEP_MAP = {
            "CO_RS_I1": {
                "titulo": "Q1 - Qual o grau de dificuldade das questões?",
                "opcoes": {"A": "Muito fácil", "B": "Fácil", "C": "Médio", "D": "Difícil", "E": "Muito difícil"}
            },
            "CO_RS_I2": {
                "titulo": "Q2 - Qual foi o tempo gasto para concluir a prova?",
                "opcoes": {"A": "< 1h", "B": "1h a 2h", "C": "3h a 4h", "D": "4h a 5h", "E": "5h (não terminei)"}
            },
            "CO_RS_I3": {
                "titulo": "Q3 - Em relação ao tempo total, a prova foi:",
                "opcoes": {"A": "Muito longa", "B": "Longa", "C": "Adequada", "D": "Curta", "E": "Muito curta"}
            },
            "CO_RS_I4": {
                "titulo": "Q4 - Os enunciados estavam claros e objetivos?",
                "opcoes": {"A": "Sim, todos", "B": "Sim, a maioria", "C": "Cerca da metade", "D": "Poucos", "E": "Não, nenhum"}
            },
            "CO_RS_I5": {
                "titulo": "Q5 - As instruções foram suficientes?",
                "opcoes": {"A": "Sim, excessivas", "B": "Sim, todas", "C": "Sim, maioria", "D": "Sim, algumas", "E": "Não, nenhuma"}
            },
            "CO_RS_I6": {
                "titulo": "Q6 - Dificuldade encontrada ao responder:",
                "opcoes": {"A": "Desconhecimento", "B": "Abordagem diferente", "C": "Espaço insuficiente", "D": "Falta motivação", "E": "Sem dificuldade"}
            },
            "CO_RS_I7": {
                "titulo": "Q7 - Sobre os conteúdos da prova:",
                "opcoes": {"A": "Não estudei maioria", "B": "Estudei alguns, não aprendi", "C": "Estudei maioria, não aprendi", "D": "Estudei/Aprendi muitos", "E": "Estudei/Aprendi todos"}
            },
            "CO_RS_I8": {
                "titulo": "Q8 - Avaliação da sequência das questões:",
                "opcoes": {"A": "Não interferiu", "B": "Preferia por área", "C": "Preferia por dificuldade", "D": "Dificultou raciocínio", "E": "Facilitou organização"}
            },
            "CO_RS_I9": {
                "titulo": "Q9 - Atividades práticas contribuíram para a resolução?",
                "opcoes": {"A": "Sim", "B": "Não"}
            }
        }

        cols_percep = [c for c in PERCEP_MAP.keys() if c in curso_df.columns]
        if not cols_percep:
            st.info("Dados de percepção de prova (CO_RS_I1...I9) não encontrados neste dataset.")
        else:
            for q_code in cols_percep:
                meta = PERCEP_MAP[q_code]
                counts = curso_df[q_code].value_counts().sort_index()
                
                labels = []
                heights = []
                colors = []
                
                possiveis = sorted(meta["opcoes"].keys())
                for letra in possiveis:
                    val = counts.get(letra, 0)
                    texto = meta["opcoes"].get(letra, letra)
                    labels.append(f"{letra}: {texto}")
                    heights.append(val)

                    if letra in ['A', 'B'] and q_code not in ['CO_RS_I1', 'CO_RS_I2', 'CO_RS_I3']: 
                         colors.append("#2E8A5C") # Verde
                    elif letra in ['D', 'E'] and q_code not in ['CO_RS_I1', 'CO_RS_I2', 'CO_RS_I3']:
                         colors.append("#8A2E2E") # Vermelho
                    else:
                         colors.append("#2E5C8A") # Azul padrão
                
                st.markdown(f"#### {meta['titulo']}")
                fig, ax = plt.subplots(figsize=(8, 3))
                bars = ax.bar(possiveis, heights, color=colors)
                ax.set_ylabel("Qtd. Estudantes")
                ax.bar_label(bars, padding=3)
                
                if heights:
                    ax.set_ylim(0, max(heights) * 1.3)
                
                caption_text = " | ".join([f"**{l}**: {t}" for l, t in meta["opcoes"].items()])
                st.caption(caption_text)
                st.pyplot(fig)
                st.markdown("---")

    # =========================
    # TAB 7) PDF PERCEPÇÃO
    # =========================
    with tab_pdf:
        st.subheader("Questionário de Percepção de Prova - Original")
        pdf_file_name = "Questionário de Percepção de Prova Enamed 2025.pdf"
        
        try:
            with open(pdf_file_name, "rb") as f:
                pdf_bytes = f.read()
                pdf_viewer(input=pdf_bytes, width=800)
        except FileNotFoundError:
            st.error(f"Arquivo PDF não encontrado: {pdf_file_name}")
            st.info("Certifique-se de que o arquivo está na pasta raiz do projeto.")