import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from textwrap import fill
import tempfile
import config # Importa as constantes
import streamlit as st # Importação necessária para exibir mensagens de erro
import urllib.error # Importação necessária para capturar o erro HTTP
from matplotlib.patches import Patch # Importação para a legenda customizada

# --- Funções de Análise (Componente Específico) ---
# (Estas funções não foram alteradas)
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

def get_score_per_subject(questions_subjects_df: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    subjects = pd.unique(questions_subjects_df[["FIRST_SUBJECT", "SECOND_SUBJECT", "THIRD_SUBJECT"]].values.ravel('K'))
    subjects = pd.Series(subjects).dropna().sort_values().unique()
    subjects_score = pd.DataFrame({"Conteúdo": subjects, "Acertos": 0})
    if df.empty or "DS_VT_ACE_OCE" not in df.columns:
        subjects_score["Nota (%)"] = 0
        return subjects_score
    marked_keys = df["DS_VT_ACE_OCE"].dropna()
    for index, row in questions_subjects_df.iterrows():
        subjects_to_update = row[["FIRST_SUBJECT", "SECOND_SUBJECT", "THIRD_SUBJECT"]].dropna().values
        if marked_keys.str.len().max() > index:
            result = marked_keys[marked_keys.str[index] == '1'].shape[0]
            subjects_score.loc[subjects_score["Conteúdo"].isin(subjects_to_update), "Acertos"] += result
    total_participants = df.shape[0]
    if total_participants > 0:
        subjects_per_question = get_subjects_per_question(questions_subjects_df)
        if len(subjects_per_question) == len(subjects_score):
            denominator = subjects_per_question * total_participants
            subject_score_column = np.divide(subjects_score["Acertos"] * 100, denominator, out=np.zeros_like(denominator, dtype=float), where=denominator!=0)
            subjects_score["Nota (%)"] = subject_score_column.round(2)
        else:
            subjects_score["Nota (%)"] = 0
    else:
        subjects_score["Nota (%)"] = 0
    invalid_subjects = get_invalid_subjects(questions_subjects_df)
    subjects_score = subjects_score[~subjects_score["Conteúdo"].isin(invalid_subjects)]
    return subjects_score

# --- Funções de Plotagem (Componente Específico) ---
# (Esta função não foi alterada)
def plot_performance_graph(Enade_2023, COURSE_CODES, group_code: int, course_code: int):
    fig1_img, fig2_img = None, None
    sk_national_df = Enade_2023[Enade_2023["CO_GRUPO"] == group_code]
    sk_ufpa_df = sk_national_df[sk_national_df["CO_CURSO"] == course_code]
    if sk_ufpa_df.empty: 
        st.warning("Não há dados de participantes para este curso.")
        return None, None, None, None
    try:
        url = config.QUESTIONS_SUBJECTS_BASE_URL + COURSE_CODES[course_code][2] + "_questions_subjects.csv"
        questions_subjects_df = pd.read_csv(url, sep=";")
    except urllib.error.HTTPError:
        st.error(f"Não foi possível carregar o arquivo de dados para o curso '{COURSE_CODES[course_code][1]}'. O arquivo não foi encontrado no repositório.")
        return None, None, None, None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados do curso: {e}")
        return None, None, None, None
    subject_score_ufpa = get_score_per_subject(questions_subjects_df, sk_ufpa_df)
    subject_score_national = get_score_per_subject(questions_subjects_df, sk_national_df)
    merged_score_df = pd.DataFrame({
        "Nota UFPA (%)": subject_score_ufpa["Nota (%)"],
        "Nota Enade (%)": subject_score_national["Nota (%)"]
    }).set_index(subject_score_national["Conteúdo"])
    ratio = lambda col: (col["Nota UFPA (%)"] / col["Nota Enade (%)"]).round(2) if col["Nota Enade (%)"] != 0 else 0
    merged_score_df["Razão"] = merged_score_df.apply(ratio, axis=1)
    fig1, ax1 = plt.subplots(figsize=(8, 8))
    merged_score_df_sorted1 = merged_score_df.sort_values(by=["Razão"]).dropna(subset=['Razão'])
    labels1 = [fill(x, 40) for x in merged_score_df_sorted1.index]
    ax1.barh(labels1, merged_score_df_sorted1["Razão"], color='k', height=0.6)
    ax1.axvline(x=1.0, color="red", linestyle='--')
    ax1.set_xlabel("Razão do percentual de acerto (UFPA / Brasil)")
    ax1.set_title(f"Razão de Acertos: {COURSE_CODES[course_code][1]}", loc='left')
    plt.tight_layout()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img1:
        fig1.savefig(tmp_img1.name, dpi=150, bbox_inches='tight')
        fig1_img = tmp_img1.name
    plt.close(fig1)
    fig2, ax2 = plt.subplots(figsize=(8, 8))
    merged_score_df_sorted2 = merged_score_df.sort_values(by=["Nota UFPA (%)"], ascending=False)
    ind = np.arange(merged_score_df_sorted2.shape[0])
    width = 0.4
    labels2 = [fill(x, 40) for x in merged_score_df_sorted2.index]
    ax2.barh(ind - width/2, merged_score_df_sorted2["Nota UFPA (%)"], width, color='dodgerblue', label="UFPA")
    ax2.barh(ind + width/2, merged_score_df_sorted2["Nota Enade (%)"], width, color='mediumspringgreen', label="Brasil")
    ax2.set(yticks=ind, yticklabels=labels2, xlim=(0, 100))
    ax2.legend()
    ax2.set_xlabel("Percentual de acerto (%)")
    ax2.set_title(f"Percentual de Acertos por Tema: {COURSE_CODES[course_code][1]}", loc='left')
    plt.tight_layout()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img2:
        fig2.savefig(tmp_img2.name, dpi=150, bbox_inches='tight')
        fig2_img = tmp_img2.name
    plt.close(fig2)
    return fig1, fig1_img, fig2, fig2_img

# --- Funções de Plotagem (Questionário do Estudante) ---

# ATUALIZADO
def plot_count_graph(QE_data_2023, course_code: int, questions_list):
    course_df = QE_data_2023[QE_data_2023["CO_CURSO"] == course_code]
    if course_df.empty: return None, None
    
    groups = {
        'Discordo Totalmente + Discordo': [1, 2],
        'Discordo Parc. + Concordo Parc.': [3, 4],
        'Concordo + Concordo Totalmente': [5, 6],
        'Não sei responder + Não se aplica': [7, 8]
    }
    colors = {
        'Discordo Totalmente + Discordo': 'red',
        'Discordo Parc. + Concordo Parc.': 'orange',
        'Concordo + Concordo Totalmente': 'green',
        'Não sei responder + Não se aplica': 'gray'
    }

    counts = {label: [] for label in groups.keys()}
    for q in questions_list:
        counts_per_q = course_df[q].value_counts()
        for label, values in groups.items():
            counts[label].append(counts_per_q.reindex(values, fill_value=0).sum())
    
    questions_labels = [q.replace('QE_I', '') for q in questions_list]
    fig, ax = plt.subplots(figsize=(10, 7))

    # --- ALTERAÇÃO: Removidos os marcadores de todas as linhas ---
    for label, data in counts.items():
        ax.plot(questions_labels, data, linestyle='-', label=label, color=colors[label], marker=None)
    
    
    # Legenda posicionada acima do gráfico
    ax.legend(
        loc='lower center',
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=False,
        fontsize='medium'
    )
    # Ajusta o layout para garantir que a legenda não seja cortada
    plt.subplots_adjust(top=0.85)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        fig.savefig(tmp_img.name, dpi=150, bbox_inches='tight')
        img_path = tmp_img.name
    plt.close(fig)
    return fig, img_path

# ATUALIZADO
def plot_average_graph(QE_data_2023, course_code: int, questions_list, question_text):
    course_df = QE_data_2023[QE_data_2023["CO_CURSO"] == course_code]
    if course_df.empty: return None, None
    
    averages = []
    for q in questions_list:
        valid_answers = course_df[q][~course_df[q].isin([7, 8])]
        if not valid_answers.empty:
            averages.append(valid_answers.mean())
        else:
            averages.append(np.nan)
            
    df_plot = pd.DataFrame({
        'Questão': [q.replace('QE_I', '') for q in questions_list],
        'Média': averages,
        'Texto': question_text
    }).dropna(subset=['Média'])
    
    if df_plot.empty: return None, None
    
    max_avg_val = df_plot['Média'].max()
    min_avg_val = df_plot['Média'].min()

    colors = ['#8FB984'] * len(df_plot)
    idx_max = df_plot['Média'].idxmax()
    idx_min = df_plot['Média'].idxmin()
    colors[idx_max] = '#1C6C0F'
    colors[idx_min] = '#F09319'
    
    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.bar(df_plot['Questão'], df_plot['Média'], color=colors)
    ax.bar_label(bars, fmt='%.2f', fontsize=10, padding=3)

    ax.set_ylim(top=ax.get_ylim()[1] * 1.1)
    
    # Legenda customizada para "Maior" e "Menor" média
    legend_elements = [
        Patch(facecolor='#1C6C0F', label=f'Maior média'),
        Patch(facecolor='#F09319', label=f'Menor média')
    ]
    ax.legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=False,
        fontsize='medium'
    )
    # Ajusta o layout para garantir que a legenda não seja cortada
    plt.subplots_adjust(top=0.85)
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        fig.savefig(tmp_img.name, dpi=150, bbox_inches='tight')
        img_path = tmp_img.name
    plt.close(fig)
    return fig, img_path


# --- FUNÇÃO DE TABELA DE RANKING RESTAURADA À LÓGICA ORIGINAL ---
# (Esta função não foi alterada)
def show_best_hei_ranking_table(Enade_2023, COURSE_CODES, hei_dict, group_code: int, course_code: int, public_only: bool):
    try:
        url = config.QUESTIONS_SUBJECTS_BASE_URL + COURSE_CODES[course_code][2] + "_questions_subjects.csv"
        questions_subjects_df = pd.read_csv(url, sep=";")
    except (urllib.error.HTTPError, FileNotFoundError):
        return pd.DataFrame({"Erro": [f"Arquivo de mapeamento de questões para o curso {COURSE_CODES[course_code][1]} não encontrado."]})
    subjects = pd.unique(questions_subjects_df[["FIRST_SUBJECT", "SECOND_SUBJECT", "THIRD_SUBJECT"]].values.ravel('K'))
    subjects = pd.Series(subjects).dropna().sort_values(ignore_index=True)
    invalid_subjects = get_invalid_subjects(questions_subjects_df)
    subjects = np.setdiff1d(subjects, invalid_subjects)
    condition = (Enade_2023["CO_GRUPO"] == group_code)
    if public_only:
        condition &= (Enade_2023["CO_CATEGAD"] == config.PUBLIC_ADMIN_CATEGORY) & \
                     (Enade_2023["CO_ORGACAD"] == config.FEDERAL_ORG_CATEGORY)
    hei_codes = pd.unique(Enade_2023.loc[condition, "CO_CURSO"])
    scores = []
    for code in hei_codes:
        hei_df = Enade_2023[(Enade_2023["CO_GRUPO"] == group_code) & (Enade_2023["CO_CURSO"] == code)]
        if not hei_df.empty:
            score = get_score_per_subject(questions_subjects_df, hei_df)["Nota (%)"].values.tolist()
            scores.append([code, score])
    if not scores:
        return pd.DataFrame({"Mensagem": ["Nenhum dado encontrado para os critérios selecionados."]})
    score_values = np.array([values[1] for values in scores])
    best_hei_scores = [(scores[row][0], max_score) 
                       for max_score, row in zip(np.max(score_values, axis=0), np.argmax(score_values, axis=0))]
    codes, subject_scores = zip(*best_hei_scores)
    get_hei_code = lambda c: Enade_2023[Enade_2023["CO_CURSO"] == c]["CO_IES"].iloc[0]
    hei_data = [hei_dict.get(get_hei_code(c), f"Código da IES: {get_hei_code(c)}") for c in codes]
    num_participants = [Enade_2023[(Enade_2023["CO_GRUPO"] == group_code) & (Enade_2023["CO_CURSO"] == c)].shape[0] for c in codes]
    ufpa_df = Enade_2023[Enade_2023["CO_CURSO"] == course_code]
    ufpa_data = get_score_per_subject(questions_subjects_df, ufpa_df).reset_index()["Nota (%)"]
    data = [subjects, hei_data, num_participants, subject_scores, ufpa_data]
    df_columns = ["Tema", "IES com o melhor desempenho", "Nº de participantes", "Melhor curso", "UFPA"]
    df_best_hei_per_subject = pd.DataFrame(dict(zip(df_columns, data)))
    df_best_hei_per_subject = df_best_hei_per_subject.rename(columns={
        "Melhor curso": "Melhor curso (%)",
        "UFPA": "UFPA (%)"
    })
    return df_best_hei_per_subject