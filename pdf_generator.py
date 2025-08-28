# pdf_generator.py

import streamlit as st
import tempfile
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter

def generate_pdf():
    """Gera o relatório completo em PDF a partir dos gráficos no st.session_state."""
    
    # Verifica se os gráficos necessários estão na sessão
    required_charts = [
        'odp_img_av', 'infra_img_av', 'oaf_img_av',
        'odp_img_co', 'infra_img_co', 'oaf_img_co',
        'razao_chart', 'percent_chart'
    ]
    if not all(key in st.session_state for key in required_charts):
        st.error("Gere todos os gráficos nas páginas de análise antes de baixar o relatório.")
        return None

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Página de Rosto (simplificada, pode ser melhorada com a capa)
    pdf.add_page()
    pdf.set_y(100)
    pdf.set_font("Times", "B", 22)
    pdf.cell(0, 10, "Relatório de Análise dos Microdados ENADE 2023", ln=True, align='C')
    curso_nome = st.session_state.get('curso_op', 'Curso não selecionado')
    municipio_nome = st.session_state.get('municipio_op', '')
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 15, f"{curso_nome} - {municipio_nome}", ln=True, align='C')
   
    # Página de Apresentação
    pdf.add_page()
    pdf.set_font("Times", "B", 16)
    pdf.cell(0, 10, "Apresentação", ln=True)
    pdf.set_font("Times", size=12)
    pdf.multi_cell(0, 6, "A CPA, em parceria com a DIAVI/PROPLAN, apresenta as análises descritivas dos microdados do Enade 2023...")
    
    # Página - Análise Conhecimento Específico
    pdf.add_page()
    pdf.set_font("Times", "B", 16)
    pdf.cell(0, 10, "Análise do Componente Específico", ln=True)
    pdf.ln(10)
    pdf.image(st.session_state['razao_chart'], x=20, w=170)
    pdf.ln(2)
    pdf.image(st.session_state['percent_chart'], x=20, w=170)

    # Página - Análise Questionário do Estudante
    pdf.add_page()
    pdf.set_font("Times", "B", 16)
    pdf.cell(0, 10, "Análise do Questionário do Estudante", ln=True)
    pdf.ln(5)

    # ODP
    pdf.set_font("Times", "B", 14)
    pdf.cell(0, 8, "Organização Didático-Pedagógica", ln=True)
    pdf.image(st.session_state['odp_img_av'], x=30, w=150)
    pdf.image(st.session_state['odp_img_co'], x=30, w=150)
    
    # Infraestrutura
    pdf.add_page()
    pdf.set_font("Times", "B", 14)
    pdf.cell(0, 8, "Infraestrutura e Instalações Físicas", ln=True)
    pdf.image(st.session_state['infra_img_av'], x=30, w=150)
    pdf.image(st.session_state['infra_img_co'], x=30, w=150)

    # OAF
    pdf.add_page()
    pdf.set_font("Times", "B", 14)
    pdf.cell(0, 8, "Oportunidades de Ampliação da Formação", ln=True)
    pdf.image(st.session_state['oaf_img_av'], x=30, w=150)
    pdf.image(st.session_state['oaf_img_co'], x=30, w=150)

    # Salvar em arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf_path = tmp_pdf.name
        pdf.output(pdf_path)

    # (Opcional) Combinar com capa e anexos
    try:
        writer = PdfWriter()
        # Adiciona a capa
        with open("src/file/capa_relatorio.pdf", "rb") as f:
            reader_capa = PdfReader(f)
            writer.add_page(reader_capa.pages[0])
        
        # Adiciona o conteúdo gerado
        with open(pdf_path, "rb") as f:
            reader_content = PdfReader(f)
            for page in reader_content.pages:
                writer.add_page(page)

        # Adiciona o anexo
        with open("anexo_qe_2023.pdf", "rb") as f:
            reader_anexo = PdfReader(f)
            for page in reader_anexo.pages:
                writer.add_page(page)

        # Salva o PDF final
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as final_pdf_file:
            final_path = final_pdf_file.name
            writer.write(final_path)
        return final_path
        
    except FileNotFoundError as e:
        st.warning(f"Não foi possível adicionar capa/anexo: {e}. Gerando PDF simples.")
        return pdf_path # Retorna o PDF sem capa e anexos se os arquivos não forem encontrados