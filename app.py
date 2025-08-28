# app.py (VERSÃO FINAL E CORRIGIDA)

import streamlit as st
from data_loader import load_data
from ui import load_css, create_sidebar, display_home_page, display_footer
from paginas import conhecimento_especifico, questionario_do_estudante, relatorio

def main():
    """
    Função principal que orquestra a execução do aplicativo Streamlit.
    """
    # --- Configuração Inicial da Página ---
    st.set_page_config(
        page_title="Enade 2023 - Análises Descritivas",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- Carregamento de Estilos e UI ---
    load_css()
    page = create_sidebar()

    # --- Carregamento dos Dados (com cache) ---
    # A função load_data é chamada apenas uma vez por sessão
    Enade_2023, QE_data_2023, UFPA_data, COURSE_CODES, hei_dict = load_data()

    # --- Roteamento de Páginas ---
    if page == "🏠 Página Inicial":
        display_home_page()

    elif "Conhecimento Específico" in page:
        # Passa todos os dados necessários para a página
        conhecimento_especifico.show_page(Enade_2023, UFPA_data, COURSE_CODES, hei_dict)

    elif "Questionário do Estudante" in page:
        questionario_do_estudante.show_page(QE_data_2023, UFPA_data, COURSE_CODES)

    elif "Baixar Relatório" in page:
        relatorio.show_page()

    # --- Rodapé ---
    display_footer()

if __name__ == "__main__":
    # O st.spinner é colocado dentro de cada página que faz processamento demorado
    # para uma melhor experiência do usuário. O carregamento inicial já é coberto
    # pela anotação @st.cache_data em load_data().
    main()