import streamlit as st
import base64
from pathlib import Path
from streamlit_option_menu import option_menu

def load_css(file_path="style/style.css"):
    """Carrega um arquivo CSS e o aplica ao app."""
    try:
        with open(file_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Arquivo CSS não encontrado em: {file_path}")

@st.cache_data
def get_base64_image(relative_path: str) -> str:
    """Converte uma imagem em string base64 para ser embutida no HTML/Markdown."""
    full_path = Path(__file__).parent / relative_path
    if not full_path.exists():
        st.error(f"❌ Imagem não encontrada no caminho: {full_path}")
        return ""
    with open(full_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def create_sidebar() -> str:
    """Cria a barra de navegação lateral e retorna a página selecionada."""
    with st.sidebar:
        st.markdown("### Menu")
        page = option_menu(
            menu_title=None,
            options=["🏠 Página Inicial", "📊 Conhecimento Específico", "📝 Questionário do Estudante", "📥 Baixar Relatório"],
            icons=["house-door-fill", "bar-chart-line-fill", "pencil-square", "download"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "17px", "color": "#4A4A4A", "padding": "8px 12px", "border-radius": "12px", "margin": "4px 0"},
                "icon": {"font-size": "18px", "margin-right": "8px"},
                "nav-link-selected": {"background-color": "rgb(209 223 255)", "font-weight": "700", "color": "#212121"},
            },
        )
    return page

def display_home_page():
    """Exibe o conteúdo da página inicial com a estrutura HTML correta e segura."""
    
    try:
        cpa_logo_b64 = get_base64_image("src/img/CPA_logo.jpg")
        proplan_logo_b64 = get_base64_image("src/img/PROPLAN_logo.jpg")
        diavi_logo_b64 = get_base64_image("src/img/DIAVI_logo.png")
        enade_title_b64 = get_base64_image("src/img/enade_removed.png")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar as imagens da página inicial: {e}")
        return

    # Montamos o HTML para o cabeçalho
    hero_html = f"""
    <div class="hero-section">
        <div class="logo-group-top-right">
            <img src="data:image/jpeg;base64,{cpa_logo_b64}" alt="Logo CPA">
            <img src="data:image/jpeg;base64,{proplan_logo_b64}" alt="Logo PROPLAN">
            <img src="data:image/png;base64,{diavi_logo_b64}" alt="Logo DIAVI">
        </div>
        <div class="title-container">
            <img src="data:image/png;base64,{enade_title_b64}" class="enade-title-image" alt="Enade 2023">
        </div>
    </div>
    """

    # Montamos o HTML para o card de introdução
    intro_html = """
    <div class="intro-card">
        <h2>Apresentação</h2>
        <div class="intro-content">
            <p>A CPA, em parceria com a DIAVI/PROPLAN, apresenta as análises descritivas dos microdados do Enade 2023, com o objetivo de auxiliar as coordenações na identificação de fragilidades para subsidiar ações corretivas e preventivas nos cursos de graduação.</p>
            <p>As análises compreendem os temas do <b>Componente Específico</b> da prova do Enade e as questões do <b>Questionário do Estudante</b>, relativas às dimensões <b>Organização Didático-pedagógica</b>, <b>Infraestrutura e Instalações Físicas</b> e <b>Oportunidade Ampliação da Formação Profissional</b>.</p>
            <p>Para visualizar as análises, utilize o menu lateral para navegar entre as páginas.</p>
            <p>A análise referente ao Componente Específico da prova do Enade foi desenvolvida por <b>Cunha, Sales e Santos (2021)</b>, conforme apresentado no artigo disponível em: <a href="https://doi.org/10.5753/wei.2021.15912">https://doi.org/10.5753/wei.2021.15912.</a></p>
        </div>
    </div>
    """

    # --- MUDANÇA CRÍTICA AQUI ---
    # Usamos st.html() para injetar o HTML. É mais robusto que st.markdown() para este caso.
    st.html(hero_html)
    st.html(intro_html)


def display_footer():
    """Exibe o rodapé da página."""
    st.markdown("""
    <div class="footer">
        <p>© 2025 CPA - DIAVI/PROPLAN. Todos os direitos reservados.</p>
    </div>
    """, unsafe_allow_html=True)