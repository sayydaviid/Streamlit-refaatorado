# data_loader.py

import pandas as pd
import streamlit as st
from zipfile import ZipFile
from io import BytesIO
from urllib.request import urlopen
import config

def get_raw_data(url: str, extract_to: str = '.') -> None:
    """Baixa um arquivo ZIP de uma URL e o extrai para um diretório."""
    http_response = urlopen(url)
    with ZipFile(BytesIO(http_response.read())) as zipfile:
        zipfile.extractall(path=extract_to)

def filter_courses_results(df: pd.DataFrame, cod_grupo_list: list) -> pd.DataFrame:
    """Filtra o DataFrame para incluir apenas participantes presentes e válidos."""
    df_filtered = df.loc[df["CO_GRUPO"].isin(cod_grupo_list)]
    df_filtered = df_filtered.loc[
        (df_filtered["TP_PRES"] == config.PRESENT_STUDENT_CODE) &
        (df_filtered["TP_PR_GER"] == config.PRESENT_STUDENT_CODE) &
        (~df_filtered["DS_VT_ESC_OCE"].isna())
    ]
    return df_filtered

def reduce_data(df: pd.DataFrame) -> pd.DataFrame:
    """Seleciona apenas as colunas relevantes para a análise dos dados."""
    columns = [
        "NU_ANO", "CO_IES", "CO_GRUPO", "CO_CURSO", "NOME_CURSO",
        "NOME_MUNIC_CURSO", "CO_CATEGAD", "CO_ORGACAD", "DS_VT_ACE_OCE",
        "DS_VT_ACE_OFG", "DS_VT_ESC_OCE", "NT_CE", "NT_GER", "NT_OBJ_CE",
        "TP_PRES", "TP_PR_GER"
    ]
    # Retorna apenas colunas que existem para evitar KeyErrors
    return df[[col for col in columns if col in df.columns]]

@st.cache_data
def load_data():
    """Função principal que orquestra o download e processamento de todos os dados."""
    database = pd.read_csv(config.BASE_DB_URL, sep=";")
    cpc2023 = pd.read_csv(config.CPC_2023_URL, sep=";")

    get_raw_data(url=config.ENADE_2023_CE_URL, extract_to='.')
    raw_data = pd.read_csv("microdados2023_arq3.txt", sep=";", decimal=",", dtype=config.DTYPES, low_memory=False)

    get_raw_data(url=config.ENADE_2023_QE_URL, extract_to='.')
    raw_QE_data_2023 = pd.read_csv("microdados2023_arq4.txt", sep=";", decimal=",", dtype=config.DTYPES, low_memory=False)

    raw_data = raw_data.merge(
        database[['CO_CURSO', 'CO_IES', 'CO_GRUPO', 'NOME_CURSO', 'NOME_MUNIC_CURSO']], on='CO_CURSO', how='left'
    )
    merged_selected_data = raw_data.merge(
        cpc2023[['CO_CURSO', 'CO_CATEGAD', 'CO_ORGACAD']], on='CO_CURSO', how='left'
    )

    UFPA_raw_data = merged_selected_data[merged_selected_data.CO_IES == config.UFPA_CODE]
    cod_grupo_list = UFPA_raw_data.CO_GRUPO.unique()
    cod_curso_list = UFPA_raw_data.CO_CURSO.unique()

    selected_data = filter_courses_results(merged_selected_data, cod_grupo_list)
    Enade_2023 = reduce_data(selected_data)

    QE_data_2023 = raw_QE_data_2023.merge(
        Enade_2023[['CO_CURSO', 'TP_PRES', 'TP_PR_GER']].drop_duplicates(), on='CO_CURSO', how='left'
    )
    for col in QE_data_2023.columns:
        if QE_data_2023[col].dtype == 'float64':
            QE_data_2023[col] = QE_data_2023[col].fillna(0).astype(int)

    UFPA_data = Enade_2023[Enade_2023.CO_IES == config.UFPA_CODE]

    COURSE_CODES = {}
    questions_sub_file_name = [
        'ENG_CIV','ENG_ELE','ARQ','ENG_COM', 'NUT', 'ENG_MEC', 'ENG_AMB','ENF', 
        'ENG_COM', 'ENG_MEC','AGR', 'ENG_AMB', 'FAR', 'ENG_ALI', 'MED', 'ENG_FLO', 
        'AGR', 'BIO', 'ENG_CIV', 'ENG_ELE', 'ENG_QUI', 'MED_VET', 'MED', 'ODO', 'FIS'
    ]
    
    for curso, file_name in zip(cod_curso_list, questions_sub_file_name):
        curso_info = UFPA_data.loc[UFPA_data['CO_CURSO'] == curso]
        if not curso_info.empty:
            COURSE_CODES[curso] = [
                curso_info['CO_GRUPO'].iloc[0],
                curso_info['NOME_CURSO'].iloc[0],
                file_name,
                curso_info['NOME_MUNIC_CURSO'].iloc[0]
            ]
    
    # --- LÓGICA ORIGINAL RESTAURADA ---
    # Este bloco é idêntico ao seu script original.
    # Ele lê o CSV sem cabeçalho e converte os valores diretamente para um dicionário.
    hei_df = pd.read_csv(config.HEI_CODES_URL, sep=",", header=None)
    hei_dict = dict(hei_df.values)
    # --- FIM DA LÓGICA ORIGINAL ---

    return Enade_2023, QE_data_2023, UFPA_data, COURSE_CODES, hei_dict