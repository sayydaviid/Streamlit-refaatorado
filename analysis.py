# analysis.py (ROBUSTO 2023 + 2025)
# - Usa NU_ITEM/NU_ITEM_X/NU_ITEM_Z quando existir no microdado + coluna equivalente no mapping
# - Acerto:
#   * se DS_VT_ACE_* tiver 0/1 -> usa '1'
#   * senão, compara DS_VT_GAB_* vs DS_VT_ESC_* (2025: OBJ)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from textwrap import fill
import tempfile
import config
import streamlit as st
import urllib.error
from matplotlib.patches import Patch

# ============================================================
# Helpers de compatibilidade
# ============================================================

def _pick_first_existing_col(df: pd.DataFrame, candidates: list) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_int_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def _get_answer_key_series(df: pd.DataFrame) -> pd.Series:
    col = _pick_first_existing_col(df, ["DS_VT_ACE_OCE", "DS_VT_ACE_OBJ"])
    if col is None or df.empty:
        return pd.Series(dtype="object")
    return df[col].dropna()


def _get_item_col(df: pd.DataFrame) -> str | None:
    return _pick_first_existing_col(df, ["NU_ITEM", "NU_ITEM_X", "NU_ITEM_Z"])


def _get_item_col_in_mapping(mapping_df: pd.DataFrame) -> str | None:
    # ajuste se seus CSVs tiverem outro nome
    return _pick_first_existing_col(
        mapping_df,
        ["NU_ITEM", "ITEM", "QUESTAO", "QUESTION", "ID_ITEM", "CO_ITEM", "NU_ITEM_X", "NU_ITEM_Z"],
    )


def _get_gabarito_col(df: pd.DataFrame) -> str | None:
    return _pick_first_existing_col(df, ["DS_VT_GAB_OBJ", "DS_VT_GAB_OCE", "DS_VT_GAB_OFG"])


def _get_marcado_col(df: pd.DataFrame) -> str | None:
    return _pick_first_existing_col(df, ["DS_VT_ESC_OBJ", "DS_VT_ESC_OCE", "DS_VT_ESC_OFG"])


def _count_correct_at_pos(df: pd.DataFrame, pos: int) -> int:
    """
    Conta quantos participantes acertaram a posição `pos` (0-based).
    Regra:
      1) Se DS_VT_ACE_* tiver 0/1, usa '1'
      2) Senão, compara DS_VT_GAB_* vs DS_VT_ESC_*
    """
    if df is None or df.empty:
        return 0

    ace = _get_answer_key_series(df)
    if not ace.empty:
        # tenta usar 0/1
        ch = ace.astype(str).str[pos]
        if ch.isin(["0", "1"]).any():
            return int((ch == "1").sum())

    gab_col = _get_gabarito_col(df)
    esc_col = _get_marcado_col(df)
    if gab_col is None or esc_col is None:
        return 0

    gab = df[gab_col].astype(str).str[pos]
    esc = df[esc_col].astype(str).str[pos]

    # Regras mínimas de validade (pelo seu exemplo, '.' significa vazio)
    # Também ignora gabarito '6' (aparece no seu gabarito) como "item não comparável"
    valid = (
        gab.notna() & esc.notna() &
        (gab != ".") & (esc != ".") &
        (gab != "6")
    )

    return int(((esc == gab) & valid).sum())


# ============================================================
# Funções de Análise (Componente Específico)
# ============================================================

def get_subjects_per_question(questions_subjects_df: pd.DataFrame) -> np.ndarray:
    subjects_columns = ["FIRST_SUBJECT", "SECOND_SUBJECT", "THIRD_SUBJECT"]
    subjects_per_question = (
        questions_subjects_df[subjects_columns]
        .stack()
        .value_counts()
        .sort_index()
        .astype(int)
    )
    return subjects_per_question.values


def get_invalid_subjects(questions_subjects_df: pd.DataFrame) -> list:
    if "VALIDITY" not in questions_subjects_df.columns:
        return []
    invalid_subjects = questions_subjects_df.groupby("FIRST_SUBJECT")["VALIDITY"].any()
    return invalid_subjects[~invalid_subjects].index.tolist()


def _get_all_subjects(questions_subjects_df: pd.DataFrame) -> np.ndarray:
    subjects = pd.unique(
        questions_subjects_df[["FIRST_SUBJECT", "SECOND_SUBJECT", "THIRD_SUBJECT"]].values.ravel("K")
    )
    return pd.Series(subjects).dropna().sort_values().unique()


def get_score_per_subject(questions_subjects_df: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """
    ROBUSTO:
    - Preferência: usar coluna de item no mapping (NU_ITEM etc) -> item-1 vira posição na string.
    - Se não existir coluna de item no mapping, cai no fallback posicional (index da linha do mapping).
    - Acertos:
      * se vetor 0/1 existir -> usa
      * senão -> compara gabarito vs marcado
    """
    subjects = _get_all_subjects(questions_subjects_df)
    subjects_score = pd.DataFrame({"Conteúdo": subjects, "Acertos": 0})

    if df is None or df.empty:
        subjects_score["Nota (%)"] = 0
        return subjects_score

    # garante que temos ao menos algo pra operar
    ace_series = _get_answer_key_series(df)
    gab_col = _get_gabarito_col(df)
    esc_col = _get_marcado_col(df)

    if ace_series.empty and (gab_col is None or esc_col is None):
        subjects_score["Nota (%)"] = 0
        return subjects_score

    # --------------- Caminho por ITEM (recomendado) ---------------
    item_col_map = _get_item_col_in_mapping(questions_subjects_df)
    if item_col_map is not None:
        qs = questions_subjects_df.copy()
        qs["_ITEM_"] = _safe_int_series(qs[item_col_map])
        qs = qs.dropna(subset=["_ITEM_"])

        item_to_subjects: dict[int, list] = {}
        for _, row in qs.iterrows():
            it = int(row["_ITEM_"])
            subs = [row.get("FIRST_SUBJECT"), row.get("SECOND_SUBJECT"), row.get("THIRD_SUBJECT")]
            subs = [s for s in subs if pd.notna(s)]
            if subs:
                item_to_subjects[it] = subs

        if item_to_subjects:
            total_participants = int(df.shape[0])

            # pega um "max_len" seguro olhando para ACE ou, se não der, pelo gabarito
            max_len = None
            if not ace_series.empty:
                max_len = ace_series.astype(str).str.len().max()
            if (max_len is None or pd.isna(max_len)) and gab_col is not None:
                max_len = df[gab_col].astype(str).str.len().max()

            if max_len is None or pd.isna(max_len) or max_len <= 0:
                subjects_score["Nota (%)"] = 0
                return subjects_score

            # itens válidos do mapping que cabem na string (pos = item-1)
            valid_items = [it for it in item_to_subjects.keys() if 1 <= it <= int(max_len)]

            # conta acertos por item
            acertos_por_item: dict[int, int] = {}
            for it in valid_items:
                pos = it - 1
                acertos_por_item[it] = _count_correct_at_pos(df, pos)

            # soma por assunto
            for it, n_acertos in acertos_por_item.items():
                subs = item_to_subjects.get(it, [])
                if subs:
                    subjects_score.loc[subjects_score["Conteúdo"].isin(subs), "Acertos"] += n_acertos

            # denominador: nº de itens (por assunto) * participantes
            subject_item_counts = {s: 0 for s in subjects_score["Conteúdo"].tolist()}
            for it in valid_items:
                for s in item_to_subjects.get(it, []):
                    if s in subject_item_counts:
                        subject_item_counts[s] += 1

            denom = np.array([subject_item_counts[s] * total_participants for s in subjects_score["Conteúdo"]], dtype=float)
            numer = subjects_score["Acertos"].to_numpy(dtype=float) * 100.0
            nota = np.divide(numer, denom, out=np.zeros_like(numer), where=denom != 0)
            subjects_score["Nota (%)"] = np.round(nota, 2)

            invalid_subjects = get_invalid_subjects(questions_subjects_df)
            subjects_score = subjects_score[~subjects_score["Conteúdo"].isin(invalid_subjects)]
            return subjects_score

    # --------------- Fallback legado: posicional pelo index ---------------
    marked_keys = _get_answer_key_series(df)
    if marked_keys.empty:
        # sem vetor 0/1 e sem mapping por item -> não dá pra inferir
        subjects_score["Nota (%)"] = 0
        return subjects_score

    max_len = marked_keys.astype(str).str.len().max()
    if pd.isna(max_len):
        subjects_score["Nota (%)"] = 0
        return subjects_score

    for idx, row in questions_subjects_df.iterrows():
        subs = row[["FIRST_SUBJECT", "SECOND_SUBJECT", "THIRD_SUBJECT"]].dropna().values
        if int(max_len) > idx:
            result = int((marked_keys.astype(str).str[idx] == "1").sum())
            subjects_score.loc[subjects_score["Conteúdo"].isin(subs), "Acertos"] += result

    total_participants = df.shape[0]
    subjects_per_question = get_subjects_per_question(questions_subjects_df)
    if len(subjects_per_question) == len(subjects_score) and total_participants > 0:
        denominator = subjects_per_question * total_participants
        subject_score_column = np.divide(
            subjects_score["Acertos"] * 100,
            denominator,
            out=np.zeros_like(denominator, dtype=float),
            where=denominator != 0,
        )
        subjects_score["Nota (%)"] = subject_score_column.round(2)
    else:
        subjects_score["Nota (%)"] = 0

    invalid_subjects = get_invalid_subjects(questions_subjects_df)
    subjects_score = subjects_score[~subjects_score["Conteúdo"].isin(invalid_subjects)]
    return subjects_score


# ============================================================
# Plotagem (Conhecimento Específico)
# ============================================================

def plot_performance_graph(Enade, COURSE_CODES, group_code: int, course_code: int):
    fig1_img, fig2_img = None, None

    sk_national_df = Enade[Enade["CO_GRUPO"] == group_code]
    sk_ufpa_df = sk_national_df[sk_national_df["CO_CURSO"] == course_code]

    if sk_ufpa_df.empty:
        st.warning("Não há dados de participantes para este curso.")
        return None, None, None, None

    try:
        url = config.QUESTIONS_SUBJECTS_BASE_URL + COURSE_CODES[course_code][2] + "_questions_subjects.csv"
        questions_subjects_df = pd.read_csv(url, sep=";")
    except urllib.error.HTTPError:
        st.error(
            f"Não foi possível carregar o arquivo de dados para o curso '{COURSE_CODES[course_code][1]}'. "
            "O arquivo não foi encontrado no repositório."
        )
        return None, None, None, None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados do curso: {e}")
        return None, None, None, None

    subject_score_ufpa = get_score_per_subject(questions_subjects_df, sk_ufpa_df)
    subject_score_national = get_score_per_subject(questions_subjects_df, sk_national_df)

    merged_score_df = pd.DataFrame(
        {
            "Nota UFPA (%)": subject_score_ufpa["Nota (%)"].values,
            "Nota Enade (%)": subject_score_national["Nota (%)"].values,
        },
        index=subject_score_national["Conteúdo"].values,
    )

    def ratio(row):
        return (row["Nota UFPA (%)"] / row["Nota Enade (%)"]).round(2) if row["Nota Enade (%)"] != 0 else np.nan

    merged_score_df["Razão"] = merged_score_df.apply(ratio, axis=1)

    # FIG 1
    fig1, ax1 = plt.subplots(figsize=(8, 8))
    merged_score_df_sorted1 = merged_score_df.sort_values(by=["Razão"]).dropna(subset=["Razão"])
    labels1 = [fill(x, 40) for x in merged_score_df_sorted1.index]
    ax1.barh(labels1, merged_score_df_sorted1["Razão"], color="k", height=0.6)
    ax1.axvline(x=1.0, color="red", linestyle="--")
    ax1.set_xlabel("Razão do percentual de acerto (UFPA / Brasil)")
    ax1.set_title(f"Razão de Acertos: {COURSE_CODES[course_code][1]}", loc="left")
    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img1:
        fig1.savefig(tmp_img1.name, dpi=150, bbox_inches="tight")
        fig1_img = tmp_img1.name
    plt.close(fig1)

    # FIG 2
    fig2, ax2 = plt.subplots(figsize=(8, 8))
    merged_score_df_sorted2 = merged_score_df.sort_values(by=["Nota UFPA (%)"], ascending=False)
    ind = np.arange(merged_score_df_sorted2.shape[0])
    width = 0.4
    labels2 = [fill(x, 40) for x in merged_score_df_sorted2.index]

    ax2.barh(ind - width / 2, merged_score_df_sorted2["Nota UFPA (%)"], width, color="dodgerblue", label="UFPA")
    ax2.barh(ind + width / 2, merged_score_df_sorted2["Nota Enade (%)"], width, color="mediumspringgreen", label="Brasil")

    ax2.set(yticks=ind, yticklabels=labels2, xlim=(0, 100))
    ax2.legend()
    ax2.set_xlabel("Percentual de acerto (%)")
    ax2.set_title(f"Percentual de Acertos por Tema: {COURSE_CODES[course_code][1]}", loc="left")
    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img2:
        fig2.savefig(tmp_img2.name, dpi=150, bbox_inches="tight")
        fig2_img = tmp_img2.name
    plt.close(fig2)

    return fig1, fig1_img, fig2, fig2_img


# ============================================================
# Plotagem (Questionário do Estudante) - mantém
# ============================================================

def plot_count_graph(QE_data, course_code: int, questions_list):
    course_df = QE_data[QE_data["CO_CURSO"] == course_code]
    if course_df.empty:
        return None, None

    groups = {
        "Discordo Totalmente + Discordo": [1, 2],
        "Discordo Parc. + Concordo Parc.": [3, 4],
        "Concordo + Concordo Totalmente": [5, 6],
        "Não sei responder + Não se aplica": [7, 8],
    }
    colors = {
        "Discordo Totalmente + Discordo": "red",
        "Discordo Parc. + Concordo Parc.": "orange",
        "Concordo + Concordo Totalmente": "green",
        "Não sei responder + Não se aplica": "gray",
    }

    counts = {label: [] for label in groups.keys()}
    for q in questions_list:
        if q not in course_df.columns:
            for label in groups.keys():
                counts[label].append(0)
            continue

        counts_per_q = course_df[q].value_counts()
        for label, values in groups.items():
            counts[label].append(counts_per_q.reindex(values, fill_value=0).sum())

    questions_labels = [q.replace("QE_I", "").replace("QE_", "") for q in questions_list]
    fig, ax = plt.subplots(figsize=(10, 7))

    for label, data in counts.items():
        ax.plot(questions_labels, data, linestyle="-", label=label, color=colors[label], marker=None)

    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, fontsize="medium")
    plt.subplots_adjust(top=0.85)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        fig.savefig(tmp_img.name, dpi=150, bbox_inches="tight")
        img_path = tmp_img.name
    plt.close(fig)
    return fig, img_path


def plot_average_graph(QE_data, course_code: int, questions_list, question_text):
    course_df = QE_data[QE_data["CO_CURSO"] == course_code]
    if course_df.empty:
        return None, None

    averages = []
    for q in questions_list:
        if q not in course_df.columns:
            averages.append(np.nan)
            continue

        valid_answers = course_df[q][~course_df[q].isin([7, 8])]
        averages.append(valid_answers.mean() if not valid_answers.empty else np.nan)

    df_plot = pd.DataFrame(
        {
            "Questão": [q.replace("QE_I", "").replace("QE_", "") for q in questions_list],
            "Média": averages,
            "Texto": question_text,
        }
    ).dropna(subset=["Média"])

    if df_plot.empty:
        return None, None

    colors = ["#8FB984"] * len(df_plot)
    idx_max = df_plot["Média"].idxmax()
    idx_min = df_plot["Média"].idxmin()
    colors[df_plot.index.get_loc(idx_max)] = "#1C6C0F"
    colors[df_plot.index.get_loc(idx_min)] = "#F09319"

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.bar(df_plot["Questão"], df_plot["Média"], color=colors)
    ax.bar_label(bars, fmt="%.2f", fontsize=10, padding=3)
    ax.set_ylim(top=ax.get_ylim()[1] * 1.1)

    legend_elements = [Patch(facecolor="#1C6C0F", label="Maior média"), Patch(facecolor="#F09319", label="Menor média")]
    ax.legend(handles=legend_elements, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, fontsize="medium")
    plt.subplots_adjust(top=0.85)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        fig.savefig(tmp_img.name, dpi=150, bbox_inches="tight")
        img_path = tmp_img.name
    plt.close(fig)
    return fig, img_path


# ============================================================
# Ranking
# ============================================================

def show_best_hei_ranking_table(Enade, COURSE_CODES, hei_dict, group_code: int, course_code: int, public_only: bool):
    try:
        url = config.QUESTIONS_SUBJECTS_BASE_URL + COURSE_CODES[course_code][2] + "_questions_subjects.csv"
        questions_subjects_df = pd.read_csv(url, sep=";")
    except (urllib.error.HTTPError, FileNotFoundError):
        return pd.DataFrame({"Erro": [f"Arquivo de mapeamento de questões para o curso {COURSE_CODES[course_code][1]} não encontrado."]})

    subjects = pd.unique(questions_subjects_df[["FIRST_SUBJECT", "SECOND_SUBJECT", "THIRD_SUBJECT"]].values.ravel("K"))
    subjects = pd.Series(subjects).dropna().sort_values(ignore_index=True)

    invalid_subjects = get_invalid_subjects(questions_subjects_df)
    subjects = np.setdiff1d(subjects, invalid_subjects)

    condition = (Enade["CO_GRUPO"] == group_code)
    if public_only:
        condition &= (Enade["CO_CATEGAD"] == config.PUBLIC_ADMIN_CATEGORY) & (Enade["CO_ORGACAD"] == config.FEDERAL_ORG_CATEGORY)

    hei_codes = pd.unique(Enade.loc[condition, "CO_CURSO"])

    scores = []
    for code in hei_codes:
        hei_df = Enade[(Enade["CO_GRUPO"] == group_code) & (Enade["CO_CURSO"] == code)]
        if not hei_df.empty:
            score = get_score_per_subject(questions_subjects_df, hei_df)["Nota (%)"].values.tolist()
            scores.append([code, score])

    if not scores:
        return pd.DataFrame({"Mensagem": ["Nenhum dado encontrado para os critérios selecionados."]})

    score_values = np.array([values[1] for values in scores])
    best_hei_scores = [(scores[row][0], max_score) for max_score, row in zip(np.max(score_values, axis=0), np.argmax(score_values, axis=0))]

    codes, subject_scores = zip(*best_hei_scores)

    def get_hei_code(c):
        return Enade[Enade["CO_CURSO"] == c]["CO_IES"].iloc[0]

    hei_data = [hei_dict.get(get_hei_code(c), f"Código da IES: {get_hei_code(c)}") for c in codes]
    num_participants = [Enade[(Enade["CO_GRUPO"] == group_code) & (Enade["CO_CURSO"] == c)].shape[0] for c in codes]

    ufpa_df = Enade[Enade["CO_CURSO"] == course_code]
    ufpa_data = get_score_per_subject(questions_subjects_df, ufpa_df).reset_index(drop=True)["Nota (%)"]

    data = [subjects, hei_data, num_participants, subject_scores, ufpa_data]
    df_columns = ["Tema", "IES com o melhor desempenho", "Nº de participantes", "Melhor curso", "UFPA"]

    df_best_hei_per_subject = pd.DataFrame(dict(zip(df_columns, data))).rename(
        columns={"Melhor curso": "Melhor curso (%)", "UFPA": "UFPA (%)"}
    )
    return df_best_hei_per_subject


