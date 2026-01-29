# app.py (CORRIGIDO)

import streamlit as st
import time
from data_loader import load_data
from ui import load_css, create_sidebar, display_home_page, display_footer
# Importando o módulo correto que criamos (assumindo que você salvou como questionario_do_estudante_2025 ou quest_estudante_enamed)
# Se você salvou o código anterior como 'paginas/questionario_do_estudante_2025.py', ajuste o import abaixo:
from paginas import (
    conhecimento_especifico, 
    questionario_do_estudante, 
    enamed, 
    relatorio,
    quest_estudante_enamed # Ou quest_estudante_enamed se você renomeou
)

def main():
    """
    Função principal que orquestra a execução do aplicativo Streamlit.
    """
    st.set_page_config(
        page_title="Enade · Análises Descritivas",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # ---------------------------------------------------------
    # Controle de carregamento inicial (1x por sessão)
    # ---------------------------------------------------------
    if "initial_loading_complete" not in st.session_state:
        st.session_state.initial_loading_complete = False

    if not st.session_state.initial_loading_complete:
        # ... (Código do loader mantido igual) ...
        loading_overlay_html = """
        <div id="loading-overlay">
            <div class="loader-container">
                <div class="lds-ring"><div></div><div></div><div></div><div></div></div>
                <p>Carregando dados, por favor aguarde...</p>
            </div>
        </div>
        <style>
            #loading-overlay {
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: rgba(248, 250, 252, 0.9);
                backdrop-filter: blur(8px);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: opacity 0.5s ease, visibility 0.5s ease;
                opacity: 1;
                visibility: visible;
            }
            .loader-container {
                text-align: center;
                color: #111827;
                font-family: 'Inter', sans-serif;
            }
            .loader-container p {
                margin-top: 1.5rem;
                font-size: 1.2rem;
                font-weight: 500;
            }
            .lds-ring {
                display: inline-block;
                position: relative;
                width: 64px;
                height: 64px;
            }
            .lds-ring div {
                box-sizing: border-box;
                display: block;
                position: absolute;
                width: 50px;
                height: 50px;
                margin: 8px;
                border: 6px solid #2E5C8A;
                border-radius: 50%;
                animation: lds-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
                border-color: #2E5C8A transparent transparent transparent;
            }
            .lds-ring div:nth-child(1) { animation-delay: -0.45s; }
            .lds-ring div:nth-child(2) { animation-delay: -0.3s; }
            .lds-ring div:nth-child(3) { animation-delay: -0.15s; }
            @keyframes lds-ring {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
        """

        hide_overlay_script = """
        <script>
            const overlay = document.getElementById('loading-overlay');
            if (overlay) {
                overlay.style.opacity = '0';
                overlay.style.visibility = 'hidden';
                setTimeout(() => { overlay.remove(); }, 500);
            }
        </script>
        """

        st.markdown(loading_overlay_html, unsafe_allow_html=True)
        load_data()
        st.session_state.initial_loading_complete = True
        st.markdown(hide_overlay_script, unsafe_allow_html=True)
        time.sleep(0.5)
        st.rerun()

    # ---------------------------------------------------------
    # APLICATIVO PRINCIPAL
    # ---------------------------------------------------------

    load_css()
    Enade, QE_data, UFPA_data, COURSE_CODES, hei_dict = load_data()
    page = create_sidebar()

    # ---------------------------------------------------------
    # Roteamento de páginas (LÓGICA CORRIGIDA)
    # ---------------------------------------------------------
    
    # 1. Página Inicial
    if page == "🏠 Página Inicial":
        display_home_page()

    # 2. Conhecimento Específico
    elif "Conhecimento Específico" in page:
        conhecimento_especifico.show_page(Enade, UFPA_data, COURSE_CODES, hei_dict)

    # 3. ENAMED (Geral/Desempenho)
    elif page == "🩺 ENAMED":
        enamed.show_page(Enade, UFPA_data, COURSE_CODES, hei_dict)

    # 4. Questionário do Estudante Enamed (NOVO - 2025)
    # Colocamos este PRIMEIRO ou usamos verificação exata para não cair no "in" do outro
    elif page == "Questionário do Estudante Enamed":
        # Chama o arquivo novo que criamos (certifique-se do nome do import)
        quest_estudante_enamed.show_page(QE_data, UFPA_data, COURSE_CODES, hei_dict)

    # 5. Questionário do Estudante (Padrão/Enade 2023)
    elif page == "📝 Questionário do Estudante":
        questionario_do_estudante.show_page(QE_data, UFPA_data, COURSE_CODES)
        
    # 6. Relatório
    elif "Baixar Relatório" in page:
        relatorio.show_page(Enade, QE_data, UFPA_data, COURSE_CODES, hei_dict)

    display_footer()

if __name__ == "__main__":
    main()