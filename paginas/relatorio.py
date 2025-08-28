# paginas/relatorio.py (ATUALIZADO)

import streamlit as st
import os

# ALTERAÇÃO: Importação corrigida para a estrutura modular
from pdf_generator import generate_pdf

def show_page():
    st.title("📥 Baixar Relatório Completo")
    st.markdown("---")

    # Lista de chaves necessárias no session_state para habilitar o botão
    required_keys = [
        'odp_img_av', 'infra_img_av', 'oaf_img_av',
        'odp_img_co', 'infra_img_co', 'oaf_img_co',
        'razao_chart', 'percent_chart', 'curso_op', 'municipio_op'
    ]

    # Verifica se todas as chaves existem no st.session_state
    if all(key in st.session_state and st.session_state[key] is not None for key in required_keys):
        
        curso = st.session_state['curso_op']
        municipio = st.session_state['municipio_op']
        
        st.success(f"Todos os dados para o relatório de **{curso} - {municipio}** estão prontos!")
        st.write("Clique no botão abaixo para gerar e baixar o seu relatório em PDF.")

        # MELHORIA: Adicionado um botão explícito para o usuário iniciar a geração do PDF.
        if st.button("Gerar Relatório em PDF"):
            # MELHORIA: Adicionado st.spinner para feedback ao usuário durante a geração.
            with st.spinner("Montando o relatório... Por favor, aguarde."):
                pdf_path = generate_pdf()
            
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                st.download_button(
                    label="Clique aqui para Baixar o PDF",
                    data=pdf_bytes,
                    file_name=f"Relatorio_Enade_2023_{curso}_{municipio}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Ocorreu um erro ao gerar o arquivo PDF. Tente gerar as análises novamente.")

    else:
        st.warning(
            "Ainda faltam dados para gerar o relatório completo. Por favor, siga os passos:\n"
            "1. Navegue até a página **'📊 Conhecimento Específico'** e gere uma análise.\n"
            "2. Navegue até a página **'📝 Questionário do Estudante'** e gere uma análise."
        )