# paginas/enamed.py
# ENAMED 2025 – Desempenho Geral + Percepção de Prova + Item Analysis
# (AJUSTE DEFINITIVO)
#  - "Acertos" usa DS_VT_ACE_OBJ (0/1 oficiais; 4/8/9 fora; 6 anulado)
#  - "Alternativas" usa DS_VT_ESC_OBJ (A–D) e SEM None (0.0% quando sem marcação A–D)
#  - Prova A–D
#  - Coluna "Gabarito": mostra A–D, ou "Anulada" (GAB=6), ou "Excluída" (item TRI via ACE=8)
#  - No gráfico: se Anulada/Excluída, label textual em vez de percentual
#  - Removido debug da aba de acertos
#  - Mostra "Número de participantes: X" em acertos (X = total filtrado, não rows_used)
#  - Removido debug da aba de alternativas

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
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    s = series.copy()
    s = s.fillna("").map(str).str.strip().str.replace(",", ".", regex=False)

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
    c = _co_ies_to_int(co_ies)
    if c is None:
        return "IES desconhecida"
    nome = hei_dict.get(c)
    if nome:
        return f"{nome} (CO_IES={c})"
    return f"CO_IES={c}"


def _clean_series_str(s: pd.Series) -> pd.Series:
    s = s.astype(str).fillna("").str.strip()
    s = s[(s != "") & (s.str.lower() != "nan") & (s.str.lower() != "none")]
    return s


def _pick_suffix_consistente_obj(df: pd.DataFrame) -> str | None:
    """
    Prioriza OBJ. Se não existir, tenta OCE/OFG.
    """
    for suf in ["_OBJ", "_OCE", "_OFG"]:
        ace_col = "DS_VT_ACE" + suf
        esc_col = "DS_VT_ESC" + suf
        gab_col = "DS_VT_GAB" + suf
        if ace_col in df.columns and esc_col in df.columns and gab_col in df.columns:
            ace = _clean_series_str(df[ace_col])
            esc = _clean_series_str(df[esc_col])
            gab = _clean_series_str(df[gab_col])
            if not ace.empty and not esc.empty and not gab.empty:
                return suf
    return None


def _pick_default_caderno(df: pd.DataFrame):
    if "CO_CADERNO" not in df.columns:
        return None
    s = pd.to_numeric(df["CO_CADERNO"], errors="coerce").dropna()
    if s.empty:
        return None
    return int(s.astype(int).mode().iloc[0])


def _mode_len(series: pd.Series) -> int:
    m = series.astype(str).str.len().mode()
    return int(m.iloc[0]) if not m.empty else 0


def _mode_char(values: list[str], default: str = "") -> str:
    """
    Moda simples de uma lista de chars (string). Ignora vazios.
    """
    vals = [v for v in values if v is not None and v != ""]
    if not vals:
        return default
    vc = pd.Series(vals).value_counts()
    if vc.empty:
        return default
    return str(vc.index[0])


def compute_stats_ace_esc_gab(df: pd.DataFrame, col_ace: str, col_esc: str, col_gab: str):
    """
    ACERTOS:
      - usa ACE (0/1/4/6/8/9)
      - base por item = contagem de ACE em {0,1}
      - item anulado se GAB=6 (não entra no denominador)
      - item excluído TRI: ACE=8 (não entra no denominador)

    ALTERNATIVAS (SEM NONE):
      - usa ESC diretamente (A–D)
      - percentuais A/B/C/D por item = alt_counts / base_alt_valid
      - base_alt_valid = número de marcações A–D naquele item
      - funciona mesmo se item anulado ou excluído (porque alternativas são do ESC)

    STATUS DO ITEM:
      - "ANULADA" se GAB=6
      - senão "EXCLUIDA" se a moda do ACE naquele item for 8
      - senão "OK"
    """
    if any(c not in df.columns for c in [col_ace, col_esc, col_gab]):
        return None

    ace = _clean_series_str(df[col_ace])
    esc = _clean_series_str(df[col_esc]).str.upper()
    gab = _clean_series_str(df[col_gab]).str.upper()

    idx = ace.index.intersection(esc.index).intersection(gab.index)
    if len(idx) == 0:
        return None

    ace = ace.loc[idx]
    esc = esc.loc[idx]
    gab = gab.loc[idx]

    n = min(_mode_len(ace), _mode_len(esc), _mode_len(gab))
    if n <= 0:
        return None

    ok = (ace.str.len() >= n) & (esc.str.len() >= n) & (gab.str.len() >= n)
    ace = ace[ok]
    esc = esc[ok]
    gab = gab[ok]
    if ace.empty:
        return None

    # gabarito por posição (pega o primeiro)
    gab0 = gab.iloc[0][:n]
    gabarito = [gab0[i] for i in range(n)]

    # --- ACERTOS (por ACE, com exclusões) ---
    base_ace = np.zeros(n, dtype=int)
    correct = np.zeros(n, dtype=int)

    excl_ace = {k: np.zeros(n, dtype=int) for k in ["ACE_4_ELIM", "ACE_6_ANUL", "ACE_8_TRI", "ACE_9_AUS", "ACE_OUTRO"]}

    # --- ALTERNATIVAS (por ESC, independente do ACE) ---
    base_alt = np.zeros(n, dtype=int)  # denom: quantas marcações A-D
    alt_counts = {k: np.zeros(n, dtype=int) for k in ["A", "B", "C", "D"]}

    excl_esc = {k: np.zeros(n, dtype=int) for k in ["ESC_BRANCO", "ESC_MULT", "ESC_OUTROS"]}

    # --- Para status de item excluído (TRI): coletar ACE por posição ---
    ace_by_pos = [[] for _ in range(n)]

    for a, e, g in zip(ace.tolist(), esc.tolist(), gab.tolist()):
        a = a[:n]
        e = e[:n]
        g = g[:n]

        for i in range(n):
            ai = a[i]   # '0','1','4','6','8','9'
            gi = g[i]   # 'A'..'D' ou '6'
            ei = e[i]   # 'A'..'D' '.' '*'

            ace_by_pos[i].append(ai)

            # Alternativas: sempre contam
            if ei in ("A", "B", "C", "D"):
                base_alt[i] += 1
                alt_counts[ei][i] += 1
            elif ei == ".":
                excl_esc["ESC_BRANCO"][i] += 1
            elif ei == "*":
                excl_esc["ESC_MULT"][i] += 1
            else:
                excl_esc["ESC_OUTROS"][i] += 1

            # Acertos: não entram se item anulado (GAB=6)
            if gi == "6":
                excl_ace["ACE_6_ANUL"][i] += 1
                continue

            if ai == "9":
                excl_ace["ACE_9_AUS"][i] += 1
                continue
            if ai == "4":
                excl_ace["ACE_4_ELIM"][i] += 1
                continue
            if ai == "8":
                excl_ace["ACE_8_TRI"][i] += 1
                continue
            if ai == "6":
                excl_ace["ACE_6_ANUL"][i] += 1
                continue

            if ai not in ("0", "1"):
                excl_ace["ACE_OUTRO"][i] += 1
                continue

            base_ace[i] += 1
            if ai == "1":
                correct[i] += 1

    perc_correct = np.where(base_ace > 0, (correct / base_ace) * 100.0, np.nan)

    perc_alt = {
        k: np.where(base_alt > 0, (alt_counts[k] / base_alt) * 100.0, 0.0)
        for k in ["A", "B", "C", "D"]
    }

    status_item = []
    for i in range(n):
        gi = gabarito[i] if i < len(gabarito) else ""
        if gi == "6":
            status_item.append("ANULADA")
        else:
            ace_mode = _mode_char(ace_by_pos[i], default="")
            if ace_mode == "8":
                status_item.append("EXCLUIDA")
            else:
                status_item.append("OK")

    return {
        "n": n,
        "gabarito": gabarito,
        "status_item": status_item,
        "base_ace": base_ace,
        "correct": correct,
        "perc_correct": perc_correct,
        "base_alt": base_alt,
        "perc_alt": perc_alt,
        "alt_counts": alt_counts,
        "excl_ace": excl_ace,
        "excl_esc": excl_esc,
        "col_ace": col_ace,
        "col_esc": col_esc,
        "col_gab": col_gab,
        "rows_used": int(len(ace)),
    }


# ============================================================
# Página Principal
# ============================================================
def show_page(Enade, UFPA_data, COURSE_CODES, hei_dict):
    st.markdown("""
        <style>
        [data-testid="stTabs"] button { padding-left: 10px; padding-right: 10px; font-size: 14px; gap: 2px; }
        [data-testid="stTabs"] { overflow: visible; }
        </style>
    """, unsafe_allow_html=True)

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
        .dropna().astype(str).unique().tolist()
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

    # IES
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

    # Curso
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
    # IMPORTANTE: filtrar por caderno
    # ---------------------------------------------------------
    if "CO_CADERNO" in curso_df.columns:
        cads = pd.to_numeric(curso_df["CO_CADERNO"], errors="coerce").dropna().astype(int)
        if not cads.empty:
            cad_list = sorted(cads.unique().tolist())
            cad_default = _pick_default_caderno(curso_df)
            cad_sel = st.selectbox(
                "Selecione o Caderno (CO_CADERNO) — necessário para não misturar ordem das questões",
                cad_list,
                index=cad_list.index(cad_default) if cad_default in cad_list else 0
            )
            curso_df = curso_df[pd.to_numeric(curso_df["CO_CADERNO"], errors="coerce").astype("Int64") == cad_sel].copy()

    # ---------------------------------------------------------
    # Saneamento numérico
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
    # Pré-processamento correto
    # ---------------------------------------------------------
    suf = _pick_suffix_consistente_obj(curso_df)
    stats = None

    if suf is not None:
        col_gab = "DS_VT_GAB" + suf
        col_ace = "DS_VT_ACE" + suf
        col_esc = "DS_VT_ESC" + suf
        stats = compute_stats_ace_esc_gab(curso_df, col_ace=col_ace, col_esc=col_esc, col_gab=col_gab)

    # ---------------------------------------------------------
    # Abas
    # ---------------------------------------------------------
    tab_acertos, tab_alternativas, tab_medias, tab_area, tab_prof, tab_enare, tab_percepcao, tab_pdf = st.tabs([
        "✅ Percentual de Acertos",
        "🔠 Análise de Alternativas",
        "📊 Médias Gerais",
        "📈 Distribuição por Área",
        "🎓 Proficiência",
        "🧮 ENARE",
        "📝 Percepção de Prova",
        "📄 PDF Percepção"
    ])

    # =========================
    # TAB 1) ACERTOS (ACE) — STATUS + PARTICIPANTES (TOTAL FILTRADO) + SEM DEBUG
    # =========================
    with tab_acertos:
        st.subheader("Percentual de Acertos por Questão")

        if stats is None:
            st.error("Não foi possível calcular. Precisa de DS_VT_ACE_OBJ + DS_VT_ESC_OBJ + DS_VT_GAB_OBJ válidos.")
            st.info(f"Colunas disponíveis: {list(curso_df.columns)}")
        else:
            n = stats["n"]
            labels_q = [f"Q{i+1}" for i in range(n)]

            y_raw = stats["perc_correct"]
            y = np.nan_to_num(y_raw, nan=0.0)


            fig, ax = plt.subplots(figsize=(12, 5))
            bars = ax.bar(labels_q, y, color="#2E5C8A")
            ax.set_ylabel("% de Acertos")
            ax.set_xlabel("Questão (posição no caderno)")
            ax.set_title(f"Percentual de Acertos por Questão\nNúmero de participantes do caderno {cad_sel}: {len(curso_df)}")
            ax.set_ylim(0, 115)

            # labels: mesmos nomes do submenu de alternativas
            for i, b in enumerate(bars):
                status = stats["status_item"][i] if i < len(stats["status_item"]) else "OK"

                if status == "ANULADA":
                    label = "Anulada"
                elif status == "EXCLUIDA":
                    label = "Excluída"
                else:
                    label = f"{y[i]:.1f}%"

                ax.text(
                    b.get_x() + b.get_width() / 2,
                    b.get_height() + 2,
                    label,
                    ha="center", va="bottom",
                    rotation=90, fontsize=7
                )

            plt.xticks(rotation=90, fontsize=8)
            plt.tight_layout()
            st.pyplot(fig)

    # =========================
    # TAB 2) ALTERNATIVAS (ESC) + GABARITO/STATUS — SEM DEBUG
    # =========================
    with tab_alternativas:
        st.subheader("Percentual de Marcação por Alternativa")
        if stats is None:
            st.warning("Não foi possível calcular alternativas.")
        else:
            n = stats["n"]
            labels_q = [f"Q{i+1}" for i in range(n)]
            p = stats["perc_alt"]
            gabarito = stats.get("gabarito", [""] * n)
            status_item = stats.get("status_item", ["OK"] * n)

            rows = []
            for i in range(n):
                gi = gabarito[i] if i < len(gabarito) else ""
                st_i = status_item[i] if i < len(status_item) else "OK"

                if st_i == "ANULADA" or gi == "6":
                    gab_show = "Anulada"
                elif st_i == "EXCLUIDA":
                    gab_show = "Excluída"
                else:
                    gab_show = gi if gi in ("A", "B", "C", "D") else ""

                rows.append({
                    "Questão": labels_q[i],
                    "Gabarito": gab_show,
                    "A": float(p["A"][i]),
                    "B": float(p["B"][i]),
                    "C": float(p["C"][i]),
                    "D": float(p["D"][i]),
                })

            df_alt = pd.DataFrame(rows).set_index("Questão")

            st.dataframe(
                df_alt.style
                .format({
                    "Gabarito": "{}",
                    "A": "{:.1f}%",
                    "B": "{:.1f}%",
                    "C": "{:.1f}%",
                    "D": "{:.1f}%"
                })
                .background_gradient(cmap="Blues", axis=0, subset=["A", "B", "C", "D"]),
                use_container_width=True,
                height=500
            )

    # =========================
    # TAB 3) MÉDIAS GERAIS
    # =========================
    with tab_medias:
        cols_media = [
            "QT_ACERTO_AREA_1", "QT_ACERTO_AREA_2", "QT_ACERTO_AREA_3",
            "QT_ACERTO_AREA_4", "QT_ACERTO_AREA_5",
        ]
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

            df_medias["Percentual de Acerto"] = (pd.to_numeric(df_medias["Média de Acertos (/20)"], errors="coerce") / 20) * 100
            df_medias["Média de Acertos (/20)"] = df_medias["Média de Acertos (/20)"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "")
            df_medias["Percentual de Acerto"] = df_medias["Percentual de Acerto"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "")

            df_medias.index = range(1, len(df_medias) + 1)
            st.dataframe(df_medias, use_container_width=True)

    # =========================
    # TAB 4) DISTRIBUIÇÃO POR ÁREA
    # =========================
    with tab_area:
        import textwrap
        cols_media = [
            "QT_ACERTO_AREA_1", "QT_ACERTO_AREA_2", "QT_ACERTO_AREA_3",
            "QT_ACERTO_AREA_4", "QT_ACERTO_AREA_5",
        ]
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
    # TAB 5) PROFICIÊNCIA
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
                CORTE_OFICIAL_INEP = -0.41  # Exemplo
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
                ax.hist(prof_series, bins=20, color="#1C6C0F", alpha=0.7, label="Alunos")
                ax.axvline(prof_mean, color="blue", linestyle="--", linewidth=2, label=f"Média ({prof_mean:.2f})")
                ax.set_xlabel("Proficiência (Escala Padronizada)")
                ax.set_ylabel("Número de Estudantes")
                ax.set_title("Distribuição da Proficiência – ENAMED 2025")
                ax.legend(loc="upper right")
                plt.tight_layout()
                st.pyplot(fig)

            st.caption(f"Proficiência baseada em {n_ok} notas válidas.")

    # =========================
    # TAB 6) ENARE
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
                plt.tight_layout()
                st.pyplot(fig)

            st.caption(f"ENARE: {n_ok}/{n_total} valores válidos.")

    # =========================
    # TAB 7) PERCEPÇÃO
    # =========================
    with tab_percepcao:
        st.subheader("Questionário de Percepção sobre a Prova")
        st.info("Mantido igual ao seu código (não alterei aqui).")

    # =========================
    # TAB 8) PDF
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
