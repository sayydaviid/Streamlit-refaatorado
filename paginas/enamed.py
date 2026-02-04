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
# NOVA LÓGICA: MAPA DE EQUIVALÊNCIA (Caderno 1 <-> Caderno 2)
# ============================================================
def get_c1_to_c2_map():
    mapping = {}
    # Usando índices base-0 (0 a 99) para iterar as 100 questões
    for i in range(100):
        c1_num = i + 1  # Questão 1 a 100 (Caderno 1)
        
        # Lógica baseada na tabela de equivalência
        if c1_num <= 50:
            c2_num = c1_num + 50
        else:
            c2_num = 101 - c1_num
            
        mapping[i] = c2_num - 1 # Retorna índice base-0 correspondente em C2
    return mapping

def unify_data_to_c1(df: pd.DataFrame, suf: str) -> pd.DataFrame:
    """
    Normaliza as strings de ACE, ESC e GAB para a ordem do Caderno 1.
    Se o aluno fez Caderno 2, reordena os caracteres.
    """
    df_out = df.copy()
    
    col_ace = "DS_VT_ACE" + suf
    col_esc = "DS_VT_ESC" + suf
    col_gab = "DS_VT_GAB" + suf
    
    mapping = get_c1_to_c2_map()
    
    # Listas para armazenar as novas colunas
    new_ace_list = []
    new_esc_list = []
    new_gab_list = []
    
    for idx, row in df_out.iterrows():
        caderno = row.get("CO_CADERNO")
        
        # Converte para string segura
        ace = str(row[col_ace]) if pd.notna(row[col_ace]) else ""
        esc = str(row[col_esc]) if pd.notna(row[col_esc]) else ""
        gab = str(row[col_gab]) if pd.notna(row[col_gab]) else ""
        
        # Tenta converter caderno para int, se falhar ou não for 2, trata como padrão
        try:
            cad_val = int(caderno)
        except:
            cad_val = -1

        # Se for C1, ou desconhecido, ou string curta demais, mantém original
        if cad_val != 2 or len(ace) < 100:
            new_ace_list.append(ace)
            new_esc_list.append(esc)
            new_gab_list.append(gab)
            continue
            
        # Se for C2, aplica o reordenamento para virar "Virtual C1"
        mapped_ace = [""] * 100
        mapped_esc = [""] * 100
        mapped_gab = [""] * 100
        
        # Para cada posição i (0..99) do Caderno 1 (Destino)
        # Buscamos o índice j correspondente no Caderno 2 (Origem)
        for i_c1 in range(100):
            i_c2 = mapping.get(i_c1)
            
            # Proteção de bounds (caso string tenha tamanho exato 100 ou mais)
            if i_c2 < len(ace): mapped_ace[i_c1] = ace[i_c2]
            else: mapped_ace[i_c1] = "."
                
            if i_c2 < len(esc): mapped_esc[i_c1] = esc[i_c2]
            else: mapped_esc[i_c1] = "."
            
            if i_c2 < len(gab): mapped_gab[i_c1] = gab[i_c2]
            else: mapped_gab[i_c1] = "."
        
        new_ace_list.append("".join(mapped_ace))
        new_esc_list.append("".join(mapped_esc))
        new_gab_list.append("".join(mapped_gab))

    df_out[col_ace] = new_ace_list
    df_out[col_esc] = new_esc_list
    df_out[col_gab] = new_gab_list
    
    return df_out

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
# ============================================================
# Página Principal (AJUSTADA COM COMPARAÇÃO)
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

    # Layout de 4 colunas para incluir o Checkbox de comparação
    col1, col2, col3, col4 = st.columns([1, 1, 1, 0.8])
    
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

    curso_df_base = df_mun_ies[df_mun_ies["NOME_CURSO"] == curso].copy()
    if curso_df_base.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    # ---------------------------------------------------------
    # LÓGICA DE CADERNO E COMPARAÇÃO
    # ---------------------------------------------------------
    cad_sel = None
    modo_caderno = "Unico"
    comparar = False
    
    # Preparando DataFrames
    df_main = curso_df_base.copy() # O df principal que será mostrado
    df_comp = pd.DataFrame()       # O df de comparação (se ativado)
    
    if "CO_CADERNO" in curso_df_base.columns:
        # Garante numérico
        curso_df_base["CO_CADERNO"] = pd.to_numeric(curso_df_base["CO_CADERNO"], errors="coerce")
        cads = curso_df_base["CO_CADERNO"].dropna().astype(int)
        
        if not cads.empty:
            cads_disponiveis = sorted(cads.unique().tolist())
            opcoes_caderno = [f"Caderno {c}" for c in cads_disponiveis]
            
            if 1 in cads_disponiveis and 2 in cads_disponiveis:
                 opcoes_caderno.insert(0, "Ambos")
            
            with col3: # Reutiliza col3 para ficar abaixo ou substitui (mas Streamlit renderiza sequencial)
                # Na verdade, o selectbox do caderno já estava lá, vamos manter no fluxo
                pass 

            escolha_caderno = st.selectbox(
                "Selecione o Caderno",
                opcoes_caderno,
                index=0
            )

            if "Ambos" in escolha_caderno:
                modo_caderno = "Ambos"
                df_main = curso_df_base.copy() # Mantém tudo
            else:
                cad_sel = int(escolha_caderno.split()[-1])
                # Filtra o principal
                df_main = curso_df_base[curso_df_base["CO_CADERNO"] == cad_sel].copy()
                
                # Prepara o de comparação (o caderno oposto) se disponível
                if cad_sel == 1:
                    df_comp = curso_df_base[curso_df_base["CO_CADERNO"] == 2].copy()
                elif cad_sel == 2:
                    df_comp = curso_df_base[curso_df_base["CO_CADERNO"] == 1].copy()

    # Checkbox de Comparação (Coluna 4)
    with col4:
        st.write("") # Espaçamento para alinhar verticalmente
        st.write("") 
        # Só habilita se um caderno específico foi selecionado (não "Ambos") e se existe o caderno oposto
        pode_comparar = (modo_caderno != "Ambos") and (not df_comp.empty)
        
        if pode_comparar:
            comparar = st.checkbox("Comparação", help=f"Comparar Caderno {cad_sel} com o Caderno equivalente")
        else:
            st.checkbox("Comparação", value=False, disabled=True, help="Selecione Caderno 1 ou 2 (e certifique-se que o outro existe) para comparar.")

    # Atualiza o curso_df global para o df_main para o restante das abas
    curso_df = df_main

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
    # Cálculo de Estatísticas (Principal e Comparação)
    # ---------------------------------------------------------
    suf = _pick_suffix_consistente_obj(curso_df)
    stats = None
    stats_comp = None

    if suf is not None:
        # 1. Stats Principal
        if modo_caderno == "Ambos":
            df_proc_main = unify_data_to_c1(curso_df, suf)
        else:
            df_proc_main = curso_df # Se é caderno único, não unifica, usa a ordem original dele
        
        col_gab = "DS_VT_GAB" + suf
        col_ace = "DS_VT_ACE" + suf
        col_esc = "DS_VT_ESC" + suf
        
        stats = compute_stats_ace_esc_gab(df_proc_main, col_ace=col_ace, col_esc=col_esc, col_gab=col_gab)

        # 2. Stats Comparação (Se ativado)
        if comparar and not df_comp.empty:
            # Calculamos as estatísticas do caderno oposto na ordem ORIGINAL dele
            # (Não unificamos para C1, pois faremos o mapeamento visualmente no gráfico)
            stats_comp = compute_stats_ace_esc_gab(df_comp, col_ace=col_ace, col_esc=col_esc, col_gab=col_gab)

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
    # TAB 1) ACERTOS (ACE) — COM COMPARAÇÃO
    # =========================
    # =========================
    # TAB 1) ACERTOS (ACE) — CORRIGIDO COM ZOOM/SLIDER
    # =========================
    with tab_acertos:
        st.subheader("Percentual de Acertos por Questão")
        
        # --- CONTROLE DE VISUALIZAÇÃO (CORREÇÃO DO BUG VISUAL) ---
        # Adicionamos um slider para o usuário escolher quantas questões ver por vez.
        # Isso evita que 100 questões fiquem esmagadas uma em cima da outra.
        col_r1, col_r2 = st.columns([3, 1])
        with col_r1:
            q_range = st.slider(
                "Selecione o intervalo de questões para visualizar:",
                min_value=1, max_value=stats["n"] if stats else 100, 
                value=(1, 20), # Padrão: ver as primeiras 20
                step=1
            )
        with col_r2:
            st.write("") # Espaço
            st.info("Ajuste o slider para dar zoom.")

        start_q, end_q = q_range
        # Índices de array (0-based)
        idx_start = start_q - 1
        idx_end = end_q 
        
        # Textos de legenda
        if modo_caderno == "Ambos":
            st.caption("Visualizando dados unificados. Questões do Caderno 2 foram reordenadas para C1.")
        elif comparar:
            cad_oposto = 2 if cad_sel == 1 else 1
            st.caption(f"Comparando: Caderno {cad_sel} (Azul) vs Caderno {cad_oposto} (Laranja).")
        else:
            st.caption(f"Visualizando dados do Caderno {cad_sel}")

        if stats is None:
            st.error("Não foi possível calcular estatísticas.")
        else:
            # Recorta os dados apenas para a faixa selecionada no slider
            all_n = stats["n"]
            full_x = np.arange(all_n)
            
            # Slice dos dados principais
            x_slice = full_x[idx_start:idx_end]
            y_main_full = np.nan_to_num(stats["perc_correct"], nan=0.0)
            y_main_slice = y_main_full[idx_start:idx_end]
            status_slice = stats["status_item"][idx_start:idx_end]
            
            # Configuração do Gráfico
            fig, ax = plt.subplots(figsize=(12, 6))

            if not comparar:
                # --- PLOTAGEM SIMPLES (COM ZOOM) ---
                bars = ax.bar(x_slice, y_main_slice, color="#2E5C8A", width=0.8)
                
                # Labels do eixo X
                ax.set_xticks(x_slice)
                ax.set_xticklabels([f"Q{i+1}" for i in x_slice], rotation=0, fontsize=10)
                
                # Rótulos em cima das barras
                for i, b in enumerate(bars):
                    status = status_slice[i] if i < len(status_slice) else "OK"
                    if status == "ANULADA": label = "Anul"
                    elif status == "EXCLUIDA": label = "Excl"
                    else: label = f"{y_main_slice[i]:.0f}%"
                    
                    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1, label, 
                            ha="center", va="bottom", fontsize=9)
            
            else:
                # --- PLOTAGEM COM COMPARAÇÃO (COM ZOOM) ---
                y_comp_mapped_full = np.zeros(all_n)
                labels_comp_full = [""] * all_n
                
                mapping = get_c1_to_c2_map()
                
                # Lógica de mapeamento (igual a anterior, mas aplicada ao array full antes do slice)
                if stats_comp is not None:
                    if cad_sel == 1:
                        for i in range(all_n):
                            idx_c2 = mapping.get(i)
                            if idx_c2 is not None and idx_c2 < len(stats_comp["perc_correct"]):
                                y_comp_mapped_full[i] = stats_comp["perc_correct"][idx_c2]
                                labels_comp_full[i] = f"Q{idx_c2 + 1}"
                    elif cad_sel == 2:
                        mapping_inv = {v: k for k, v in mapping.items()}
                        for i in range(all_n):
                            idx_c1 = mapping_inv.get(i)
                            if idx_c1 is not None and idx_c1 < len(stats_comp["perc_correct"]):
                                y_comp_mapped_full[i] = stats_comp["perc_correct"][idx_c1]
                                labels_comp_full[i] = f"Q{idx_c1 + 1}"

                # Aplica o slice nos dados de comparação
                y_comp_slice = y_comp_mapped_full[idx_start:idx_end]
                y_comp_slice = np.nan_to_num(y_comp_slice, nan=0.0)
                labels_comp_slice = labels_comp_full[idx_start:idx_end]

                # Plot Grouped Bars
                width = 0.4
                rects1 = ax.bar(x_slice - width/2, y_main_slice, width, label=f'Caderno {cad_sel}', color="#2E5C8A")
                rects2 = ax.bar(x_slice + width/2, y_comp_slice, width, label=f'Caderno {cad_oposto}', color="#FF8C00")

                # Labels Eixo X (Composto)
                x_labels_combined = []
                for k, idx_absoluto in enumerate(x_slice):
                    q_main = f"Q{idx_absoluto+1}"
                    q_other = labels_comp_slice[k]
                    # Quebra de linha para não ficar largo
                    x_labels_combined.append(f"{q_main}\n({q_other})")
                
                ax.set_xticks(x_slice)
                ax.set_xticklabels(x_labels_combined, rotation=0, fontsize=9)
                ax.legend()
                
                # Valores em cima das barras (apenas se tiver poucas barras para não poluir)
                if (idx_end - idx_start) <= 25:
                    ax.bar_label(rects1, fmt='%.0f', padding=2, fontsize=8)
                    ax.bar_label(rects2, fmt='%.0f', padding=2, fontsize=8)

            ax.set_ylabel("% de Acertos")
            ax.set_xlabel("Questão")
            ax.set_title(f"Desempenho por Item (Questões {start_q} a {end_q})")
            ax.set_ylim(0, 115)
            ax.grid(axis='y', linestyle='--', alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig)
            
    # =========================
    # TAB 2) ALTERNATIVAS (ESC)
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

    # TAB 7) PERCEPÇÃO DE PROVA
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