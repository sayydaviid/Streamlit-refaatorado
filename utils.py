# utils.py

import pandas as pd

def atualiza_cursos(UFPA_data: pd.DataFrame, municipio: str) -> list:
    """
    Filtra e retorna uma lista ordenada de nomes de cursos para um dado município.
    """
    cursos = UFPA_data.query("NOME_MUNIC_CURSO == @municipio")['NOME_CURSO'].unique().tolist()
    cursos.sort()
    return cursos