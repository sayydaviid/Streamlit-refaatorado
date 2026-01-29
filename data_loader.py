# data_loader.py (COMPLETO — 2023 + 2025 juntos, com LOGS e filtro 2025 corrigido)

import pandas as pd
import streamlit as st
from zipfile import ZipFile
from io import BytesIO
from urllib.request import urlopen
import config
import requests  # verificação dos links
import logging

# ============================================================
# Logger (console do Streamlit)
# ============================================================
logger = logging.getLogger("enade")

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
logger.setLevel(logging.INFO)


# ============================================================
# 1) Download/extração (mantém para 2023 ZIP)
# ============================================================
def get_raw_data(url: str, extract_to: str = ".") -> None:
    """Baixa um arquivo ZIP de uma URL e o extrai para um diretório."""
    logger.info(f"[get_raw_data] Baixando ZIP: {url}")
    http_response = urlopen(url)
    with ZipFile(BytesIO(http_response.read())) as zipfile:
        zipfile.extractall(path=extract_to)
    logger.info(f"[get_raw_data] Extraído em: {extract_to}")


# ============================================================
# 2) Filtros compatíveis (2023 e 2025) — CORRIGIDO
# ============================================================
def _non_null_any(df: pd.DataFrame, cols: list) -> pd.Series:
    """Máscara True se pelo menos uma coluna em cols não for NaN."""
    mask = pd.Series(False, index=df.index)
    for c in cols:
        if c in df.columns:
            mask = mask | (~df[c].isna())
    return mask


def _has_real_answer(series: pd.Series) -> pd.Series:
    """
    True quando a célula tem conteúdo "real":
      - não vazio
      - não é só '.' (ex.: '.....')
    Essencial no 2025 onde DS_VT_ESC_OBJ pode vir como '....'
    """
    s = series.astype("object")
    s = s.fillna("").astype(str).str.strip()
    # fullmatch: somente pontos
    return (s != "") & (~s.str.fullmatch(r"\.*"))


def filter_courses_results(df: pd.DataFrame, cod_grupo_list: list) -> pd.DataFrame:
    """
    Filtra o DataFrame para incluir apenas participantes presentes e válidos.

    Correção crítica (2025):
      - Só aplica filtro de presença (555) se esse valor existir na coluna.
        (Porque em 2025 TP_PR_GER pode ser 222, etc.)
      - Para respostas do aluno, exige conteúdo real (não só '.' e não vazio).
    """
    df_filtered = df.copy()
    logger.info(f"[filter_courses_results] IN  shape={df_filtered.shape}")

    # CO_GRUPO vem do merge com base_db
    if "CO_GRUPO" in df_filtered.columns and len(cod_grupo_list) > 0:
        before = df_filtered.shape[0]
        df_filtered = df_filtered.loc[df_filtered["CO_GRUPO"].isin(cod_grupo_list)]
        logger.info(f"[filter_courses_results] CO_GRUPO isin(list) {before}->{df_filtered.shape[0]}")
    elif "CO_GRUPO" in df_filtered.columns:
        logger.warning("[filter_courses_results] cod_grupo_list vazio — NÃO filtrando por CO_GRUPO")

    # presença: só filtra se 555 existir
    if "TP_PRES" in df_filtered.columns:
        if (df_filtered["TP_PRES"] == config.PRESENT_STUDENT_CODE).any():
            before = df_filtered.shape[0]
            df_filtered = df_filtered.loc[df_filtered["TP_PRES"] == config.PRESENT_STUDENT_CODE]
            logger.info(f"[filter_courses_results] TP_PRES==555 {before}->{df_filtered.shape[0]}")
        else:
            logger.warning("[filter_courses_results] TP_PRES não contém 555 — pulando filtro")

    if "TP_PR_GER" in df_filtered.columns:
        if (df_filtered["TP_PR_GER"] == config.PRESENT_STUDENT_CODE).any():
            before = df_filtered.shape[0]
            df_filtered = df_filtered.loc[df_filtered["TP_PR_GER"] == config.PRESENT_STUDENT_CODE]
            logger.info(f"[filter_courses_results] TP_PR_GER==555 {before}->{df_filtered.shape[0]}")
        else:
            logger.warning("[filter_courses_results] TP_PR_GER não contém 555 — pulando filtro")

    # resposta do aluno: aceita OCE ou OBJ, mas precisa ser real
    resp_cols = ["DS_VT_ESC_OCE", "DS_VT_ESC_OBJ"]
    before = df_filtered.shape[0]
    df_filtered = df_filtered.loc[_non_null_any(df_filtered, resp_cols)]
    logger.info(f"[filter_courses_results] non-null em ESC cols {before}->{df_filtered.shape[0]}")

    masks = []
    if "DS_VT_ESC_OCE" in df_filtered.columns:
        masks.append(_has_real_answer(df_filtered["DS_VT_ESC_OCE"]))
    if "DS_VT_ESC_OBJ" in df_filtered.columns:
        masks.append(_has_real_answer(df_filtered["DS_VT_ESC_OBJ"]))

    if masks:
        valid_resp_mask = masks[0]
        for m in masks[1:]:
            valid_resp_mask = valid_resp_mask | m
        before = df_filtered.shape[0]
        df_filtered = df_filtered.loc[valid_resp_mask]
        logger.info(f"[filter_courses_results] ESC real (não '.') {before}->{df_filtered.shape[0]}")

    logger.info(f"[filter_courses_results] OUT shape={df_filtered.shape}")
    return df_filtered


# ============================================================
# 3) Redução de colunas (mínimo comum + específicas)
# ============================================================
def reduce_data(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "NU_ANO",
        "CO_IES",
        "CO_GRUPO",
        "CO_CURSO",
        "NOME_CURSO",
        "NOME_MUNIC_CURSO",
        "CO_CATEGAD",
        "CO_ORGACAD",
        "TP_PRES",
        "TP_PR_GER",
        "DS_VT_ACE_OCE",
        "DS_VT_ACE_OFG",
        "DS_VT_ESC_OCE",
        "NT_CE",
        "NT_GER",
        "NT_OBJ_CE",
        "CO_CADERNO",
        "NU_ITEM",
        "NU_ITEM_Z",
        "NU_ITEM_X",
        "DS_VT_GAB_OBJ",
        "DS_VT_ACE_OBJ",
        "DS_VT_ESC_OBJ",
        "PROFICIENCIA",
        "QT_ACERTO_AREA_1",
        "QT_ACERTO_AREA_2",
        "QT_ACERTO_AREA_3",
        "QT_ACERTO_AREA_4",
        "QT_ACERTO_AREA_5",
        "PER_ACERTO_ENARE",
        "CO_RS_I1",
        "CO_RS_I2",
        "CO_RS_I3",
        "CO_RS_I4",
        "CO_RS_I5",
        "CO_RS_I6",
        "CO_RS_I7",
        "CO_RS_I8",
        "CO_RS_I9",
        "EDICAO",
    ]
    out = df[[col for col in columns if col in df.columns]].copy()
    return out


# ============================================================
# 4) Leitores (2023 ZIP e 2025 TXT)
# ============================================================
def _load_2023(database: pd.DataFrame, cpc2023: pd.DataFrame):
    logger.info("========== _load_2023 (START) ==========")

    get_raw_data(url=config.ENADE_2023_CE_URL, extract_to=".")
    raw_data = pd.read_csv(
        "microdados2023_arq3.txt",
        sep=";",
        decimal=",",
        dtype=config.DTYPES,
        low_memory=False,
    )
    logger.info(f"[2023] raw_data shape={raw_data.shape}")

    get_raw_data(url=config.ENADE_2023_QE_URL, extract_to=".")
    raw_QE_data_2023 = pd.read_csv(
        "microdados2023_arq4.txt",
        sep=";",
        decimal=",",
        dtype=config.DTYPES,
        low_memory=False,
    )
    logger.info(f"[2023] raw_QE_data shape={raw_QE_data_2023.shape}")

    raw_data = raw_data.merge(
        database[["CO_CURSO", "CO_IES", "CO_GRUPO", "NOME_CURSO", "NOME_MUNIC_CURSO"]],
        on="CO_CURSO",
        how="left",
    )

    merged_selected_data = raw_data.merge(
        cpc2023[["CO_CURSO", "CO_CATEGAD", "CO_ORGACAD"]],
        on="CO_CURSO",
        how="left",
    )
    logger.info(f"[2023] merged_selected_data shape={merged_selected_data.shape}")

    UFPA_raw_data = merged_selected_data[merged_selected_data.CO_IES == config.UFPA_CODE]
    cod_grupo_list = UFPA_raw_data.CO_GRUPO.unique()
    cod_curso_list = UFPA_raw_data.CO_CURSO.unique()
    logger.info(f"[2023] UFPA rows={UFPA_raw_data.shape[0]} | cursos={len(cod_curso_list)} | grupos={len(cod_grupo_list)}")

    selected_data = filter_courses_results(merged_selected_data, cod_grupo_list)
    Enade_2023 = reduce_data(selected_data)
    Enade_2023["EDICAO"] = "2023"
    logger.info(f"[2023] Enade_2023 shape(after filter+reduce)={Enade_2023.shape}")

    QE_data_2023 = raw_QE_data_2023.merge(
        Enade_2023[["CO_CURSO", "TP_PRES", "TP_PR_GER"]].drop_duplicates(),
        on="CO_CURSO",
        how="left",
    )
    for col in QE_data_2023.columns:
        if QE_data_2023[col].dtype == "float64":
            QE_data_2023[col] = QE_data_2023[col].fillna(0).astype(int)
    QE_data_2023["EDICAO"] = "2023"
    logger.info(f"[2023] QE_data_2023 shape={QE_data_2023.shape}")

    UFPA_data_inicial = Enade_2023[Enade_2023.CO_IES == config.UFPA_CODE].copy()
    logger.info(f"[2023] UFPA_data_inicial shape={UFPA_data_inicial.shape}")

    logger.info("========== _load_2023 (END) ==========")
    return Enade_2023, QE_data_2023, UFPA_data_inicial, cod_curso_list


def _load_2025(database: pd.DataFrame, cpc2023: pd.DataFrame):
    logger.info("========== _load_2025 (START) ==========")

    if not hasattr(config, "ENADE_2025_CE_URL") or not hasattr(config, "ENADE_2025_QE_URL"):
        raise AttributeError("Faltam ENADE_2025_CE_URL e/ou ENADE_2025_QE_URL no config.py")

    logger.info(f"[2025] CE_URL={config.ENADE_2025_CE_URL}")
    logger.info(f"[2025] QE_URL={config.ENADE_2025_QE_URL}")

    raw_data_2025 = pd.read_csv(
        config.ENADE_2025_CE_URL,
        sep=";",
        decimal=",",
        dtype=config.DTYPES,
        low_memory=False,
    )
    logger.info(f"[2025] raw_data_2025 shape={raw_data_2025.shape}")
    logger.info(f"[2025] raw_data_2025 cols={list(raw_data_2025.columns)[:20]} ...")

    raw_QE_data_2025 = pd.read_csv(
        config.ENADE_2025_QE_URL,
        sep=";",
        decimal=",",
        dtype=config.DTYPES,
        low_memory=False,
    )
    logger.info(f"[2025] raw_QE_data_2025 shape={raw_QE_data_2025.shape}")

    # Merge com base_db (provável ponto de falha se base_db for de 2023)
    raw_data_2025 = raw_data_2025.merge(
        database[["CO_CURSO", "CO_IES", "CO_GRUPO", "NOME_CURSO", "NOME_MUNIC_CURSO"]],
        on="CO_CURSO",
        how="left",
    )
    logger.info(f"[2025] after merge base_db shape={raw_data_2025.shape}")

    # Diagnóstico do merge
    for c in ["CO_IES", "CO_GRUPO", "NOME_CURSO", "NOME_MUNIC_CURSO"]:
        if c in raw_data_2025.columns:
            logger.info(f"[2025] {c} nulos após merge: {raw_data_2025[c].isna().sum()} / {len(raw_data_2025)}")

    merged_selected_2025 = raw_data_2025.merge(
        cpc2023[["CO_CURSO", "CO_CATEGAD", "CO_ORGACAD"]],
        on="CO_CURSO",
        how="left",
    )
    logger.info(f"[2025] merged_selected_2025 shape={merged_selected_2025.shape}")

    # UFPA depende de CO_IES vir preenchido no merge
    if "CO_IES" in merged_selected_2025.columns:
        UFPA_raw_data_2025 = merged_selected_2025[merged_selected_2025.CO_IES == config.UFPA_CODE]
    else:
        UFPA_raw_data_2025 = merged_selected_2025.iloc[0:0].copy()

    cod_grupo_list_2025 = UFPA_raw_data_2025.CO_GRUPO.unique() if "CO_GRUPO" in UFPA_raw_data_2025.columns else []
    cod_curso_list_2025 = UFPA_raw_data_2025.CO_CURSO.unique() if "CO_CURSO" in UFPA_raw_data_2025.columns else []

    logger.info(f"[2025] UFPA rows={UFPA_raw_data_2025.shape[0]} | cursos={len(cod_curso_list_2025)} | grupos={len(cod_grupo_list_2025)}")

    selected_2025 = filter_courses_results(merged_selected_2025, cod_grupo_list_2025)
    Enade_2025 = reduce_data(selected_2025)
    Enade_2025["EDICAO"] = "2025"
    logger.info(f"[2025] Enade_2025 shape(after filter+reduce)={Enade_2025.shape}")

    # QE 2025: injeta TP_PRES/TP_PR_GER se existirem
    join_cols = ["CO_CURSO"]
    extra = [c for c in ["TP_PRES", "TP_PR_GER"] if c in Enade_2025.columns]
    if extra:
        QE_2025 = raw_QE_data_2025.merge(
            Enade_2025[join_cols + extra].drop_duplicates(),
            on="CO_CURSO",
            how="left",
        )
    else:
        QE_2025 = raw_QE_data_2025.copy()

    for col in QE_2025.columns:
        if QE_2025[col].dtype == "float64":
            QE_2025[col] = QE_2025[col].fillna(0).astype(int)

    QE_2025["EDICAO"] = "2025"
    logger.info(f"[2025] QE_2025 shape={QE_2025.shape}")

    UFPA_data_inicial_2025 = Enade_2025[Enade_2025.CO_IES == config.UFPA_CODE].copy() if "CO_IES" in Enade_2025.columns else Enade_2025.iloc[0:0].copy()
    logger.info(f"[2025] UFPA_data_inicial_2025 shape={UFPA_data_inicial_2025.shape}")

    logger.info("========== _load_2025 (END) ==========")
    return Enade_2025, QE_2025, UFPA_data_inicial_2025, cod_curso_list_2025


# ============================================================
# 5) load_data (2023 + 2025 juntos)
# ============================================================
@st.cache_data
def load_data():
    logger.info("========== load_data (START) ==========")

    database = pd.read_csv(config.BASE_DB_URL, sep=";")
    cpc2023 = pd.read_csv(config.CPC_2023_URL, sep=";")
    logger.info(f"[load_data] base_db shape={database.shape} | CPC shape={cpc2023.shape}")

    Enade_2023, QE_2023, UFPA_2023, cursos_2023 = _load_2023(database, cpc2023)
    Enade_2025, QE_2025, UFPA_2025, cursos_2025 = _load_2025(database, cpc2023)

    Enade_ALL = pd.concat([Enade_2023, Enade_2025], ignore_index=True)
    QE_ALL = pd.concat([QE_2023, QE_2025], ignore_index=True)
    UFPA_data_inicial = pd.concat([UFPA_2023, UFPA_2025], ignore_index=True)

    logger.info(f"[load_data] Enade_ALL shape={Enade_ALL.shape}")
    logger.info(f"[load_data] QE_ALL shape={QE_ALL.shape}")
    logger.info(f"[load_data] UFPA_data_inicial shape={UFPA_data_inicial.shape}")

    if "EDICAO" in Enade_ALL.columns:
        logger.info("[load_data] Enade_ALL por EDICAO:\n%s", Enade_ALL["EDICAO"].value_counts(dropna=False).to_string())

    # cursos UFPA (união)
    cod_curso_list = pd.unique(pd.Series(list(cursos_2023) + list(cursos_2025))).tolist()
    logger.info(f"[load_data] cursos UFPA (união): {len(cod_curso_list)}")

    # -------------------
    # COURSE_CODES (igual ao seu)
    # -------------------
    COURSE_CODES = {}
    questions_sub_file_name = [
        "ENG_CIV", "ENG_ELE", "ARQ", "ENG_COM", "NUT", "ENG_MEC", "ENG_AMB", "ENF",
        "ENG_COM", "ENG_MEC", "AGR", "ENG_AMB", "FAR", "ENG_ALI", "MED", "ENG_FLO",
        "AGR", "BIO", "ENG_CIV", "ENG_ELE", "ENG_QUI", "MED_VET", "MED", "ODO", "FIS"
    ]

    for i, curso_code in enumerate(cod_curso_list):
        if i < len(questions_sub_file_name):
            curso_info = UFPA_data_inicial.loc[UFPA_data_inicial["CO_CURSO"] == curso_code]
            if not curso_info.empty:
                COURSE_CODES[curso_code] = [
                    curso_info["CO_GRUPO"].iloc[0] if "CO_GRUPO" in curso_info.columns else None,
                    curso_info["NOME_CURSO"].iloc[0] if "NOME_CURSO" in curso_info.columns else str(curso_code),
                    questions_sub_file_name[i],
                    curso_info["NOME_MUNIC_CURSO"].iloc[0] if "NOME_MUNIC_CURSO" in curso_info.columns else ""
                ]

    logger.info(f"[load_data] COURSE_CODES montado: {len(COURSE_CODES)}")

    # --- VERIFICAÇÃO DE ARQUIVOS ---
    with st.spinner("Verificando a disponibilidade dos dados para os cursos..."):
        cursos_validos = {}
        for code, details in COURSE_CODES.items():
            file_name = details[2]
            url_to_check = f"{config.QUESTIONS_SUBJECTS_BASE_URL}{file_name}_questions_subjects.csv"
            try:
                response = requests.head(url_to_check, timeout=5)
                if response.status_code == 200:
                    cursos_validos[code] = details
            except requests.RequestException:
                pass

        COURSE_CODES_VALIDOS = cursos_validos
    logger.info(f"[load_data] COURSE_CODES_VALIDOS: {len(COURSE_CODES_VALIDOS)}")

    # ------------------------------------------------------------
    # FILTRO CORRETO:
    # - UFPA_data e QE: por CO_CURSO (UFPA)
    # - Enade_ALL (base nacional): por CO_GRUPO (grupos dos cursos validados)
    # ------------------------------------------------------------
    ufpa_cursos_validos = list(COURSE_CODES_VALIDOS.keys())

    # grupos válidos (para manter o "Brasil" na base do Enade)
    grupos_validos = sorted(
        list({details[0] for _, details in COURSE_CODES_VALIDOS.items() if details and details[0] is not None})
    )

    logger.info(f"[load_data] ufpa_cursos_validos={len(ufpa_cursos_validos)} | grupos_validos={len(grupos_validos)}")

    # UFPA (somente cursos validados)
    UFPA_data_VALIDA = UFPA_data_inicial[
        UFPA_data_inicial["CO_CURSO"].isin(ufpa_cursos_validos)
    ].copy()

    # ENADE (NACIONAL): filtra por grupo, NÃO por CO_CURSO
    if "CO_GRUPO" in Enade_ALL.columns and grupos_validos:
        Enade_ALL_VALIDA = Enade_ALL[
            Enade_ALL["CO_GRUPO"].isin(grupos_validos)
        ].copy()
    else:
        Enade_ALL_VALIDA = Enade_ALL.copy()
        logger.warning("[load_data] Enade_ALL não tem CO_GRUPO ou grupos_validos vazio — mantendo Enade_ALL inteiro")

    # QE: aqui sim faz sentido filtrar por CO_CURSO (UFPA)
    QE_ALL_VALIDA = QE_ALL[
        QE_ALL["CO_CURSO"].isin(ufpa_cursos_validos)
    ].copy()

    logger.info(f"[load_data] UFPA_data_VALIDA shape={UFPA_data_VALIDA.shape}")
    logger.info(f"[load_data] Enade_ALL_VALIDA (NACIONAL) shape={Enade_ALL_VALIDA.shape}")
    logger.info(f"[load_data] QE_ALL_VALIDA shape={QE_ALL_VALIDA.shape}")

    if "EDICAO" in Enade_ALL_VALIDA.columns:
        logger.info(
            "[load_data] Enade_ALL_VALIDA por EDICAO:\n%s",
            Enade_ALL_VALIDA["EDICAO"].value_counts(dropna=False).to_string()
        )

    # HEI dict (igual)
    hei_df = pd.read_csv(config.HEI_CODES_URL)
    hei_dict = dict(hei_df.values)

    return Enade_ALL_VALIDA, QE_ALL_VALIDA, UFPA_data_VALIDA, COURSE_CODES_VALIDOS, hei_dict
