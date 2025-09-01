import streamlit as st
import time
from data_loader import load_data
from ui import load_css, create_sidebar, display_home_page, display_footer
from paginas import conhecimento_especifico, questionario_do_estudante, relatorio

def main():
    """
    Função principal que orquestra a execução do aplicativo Streamlit.
    """
    st.set_page_config(
        page_title="Enade 2023 - Análises Descritivas",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Inicializa o estado de carregamento na sessão
    if 'initial_loading_complete' not in st.session_state:
        st.session_state.initial_loading_complete = False

    # Lógica para executar a tela de carregamento APENAS UMA VEZ por sessão
    if not st.session_state.initial_loading_complete:
        # HTML e CSS da sobreposição
        loading_overlay_html = """
        <div id="loading-overlay">
            <div class="loader-container">
                <div class="lds-ring"><div></div><div></div><div></div><div></div></div>
                <p>Carregando dados, por favor aguarde...</p>
            </div>
        </div>
        <style>
            #loading-overlay {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: rgba(248, 250, 252, 0.9); backdrop-filter: blur(8px);
                z-index: 9999; display: flex; align-items: center; justify-content: center;
                transition: opacity 0.5s ease, visibility 0.5s ease; opacity: 1; visibility: visible;
            }
            .loader-container { text-align: center; color: #111827; font-family: 'Inter', sans-serif; }
            .loader-container p { margin-top: 1.5rem; font-size: 1.2rem; font-weight: 500; }
            .lds-ring { display: inline-block; position: relative; width: 64px; height: 64px; }
            .lds-ring div {
                box-sizing: border-box; display: block; position: absolute; width: 50px;
                height: 50px; margin: 8px; border: 6px solid #2E5C8A; border-radius: 50%;
                animation: lds-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
                border-color: #2E5C8A transparent transparent transparent;
            }
            .lds-ring div:nth-child(1) { animation-delay: -0.45s; }
            .lds-ring div:nth-child(2) { animation-delay: -0.3s; }
            .lds-ring div:nth-child(3) { animation-delay: -0.15s; }
            @keyframes lds-ring { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
        """
        # Script para esconder a sobreposição
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
        
        # Mostra a sobreposição
        st.markdown(loading_overlay_html, unsafe_allow_html=True)
        
        # Carrega os dados (isso vai popular o cache do Streamlit)
        load_data()
        
        # Marca que o carregamento foi completo
        st.session_state.initial_loading_complete = True
        
        # Injeta o script para remover a sobreposição
        st.markdown(hide_overlay_script, unsafe_allow_html=True)
        
        # Dá um pequeno tempo para a animação de fade-out acontecer antes de re-executar
        time.sleep(0.5)
        
        # Força a re-execução do script. Da próxima vez, o bloco 'if' será pulado.
        st.rerun()

    # --- O APLICATIVO PRINCIPAL RODA A PARTIR DAQUI ---
    # Esta parte do código só é executada após o carregamento inicial

    # Carregamento de Estilos
    load_css()

    # Carregamento dos Dados (agora instantâneo, vindo do cache)
    Enade_2023, QE_data_2023, UFPA_data, COURSE_CODES, hei_dict = load_data()

    # Criação da UI principal
    page = create_sidebar()

    # Roteamento de Páginas
    if page == "🏠 Página Inicial":
        display_home_page()
    elif "Conhecimento Específico" in page:
        conhecimento_especifico.show_page(Enade_2023, UFPA_data, COURSE_CODES, hei_dict)
    elif "Questionário do Estudante" in page:
        questionario_do_estudante.show_page(QE_data_2023, UFPA_data, COURSE_CODES)
    elif "Baixar Relatório" in page:
        relatorio.show_page(Enade_2023, QE_data_2023, UFPA_data, COURSE_CODES, hei_dict)    

    # Rodapé
    display_footer()

if __name__ == "__main__":
    main()