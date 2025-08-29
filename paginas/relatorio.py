import streamlit as st
import os

# Importação da sua função de gerar PDF
from pdf_generator import generate_pdf

def show_page():
    st.title("📥 Baixar Relatório Completo")
    st.markdown("---")

    # --- ALTERAÇÃO: Inicializa o estado do PDF no session_state ---
    # Isso garante que a variável exista na sessão do usuário.
    if 'pdf_bytes' not in st.session_state:
        st.session_state.pdf_bytes = None

    # Lista de chaves necessárias para habilitar a geração
    required_keys = [
        'odp_img_av', 'infra_img_av', 'oaf_img_av',
        'odp_img_co', 'infra_img_co', 'oaf_img_co',
        'razao_chart', 'percent_chart', 'curso_op', 'municipio_op'
    ]

    # Verifica se todas as análises foram geradas
    if all(key in st.session_state and st.session_state[key] is not None for key in required_keys):
        
        curso = st.session_state['curso_op']
        municipio = st.session_state['municipio_op']
        
        st.success(f"Todos os dados para o relatório de **{curso} - {municipio}** estão prontos!")
        st.write("Clique no botão abaixo para gerar o seu relatório em PDF.")

        # Botão para iniciar a geração do PDF
        if st.button("Gerar Relatório em PDF"):
            with st.spinner("Montando o relatório... Por favor, aguarde."):
                pdf_path = generate_pdf()
            
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        # --- ALTERAÇÃO: Salva os bytes do PDF no session_state ---
                        st.session_state.pdf_bytes = f.read()
                else:
                    # Limpa o estado se a geração falhar
                    st.session_state.pdf_bytes = None
                    st.error("Ocorreu um erro ao gerar o arquivo PDF. Tente gerar as análises novamente.")

        # --- ALTERAÇÃO: Lógica para exibir o botão de download de forma persistente ---
        # Se os bytes do PDF existem no estado da sessão, o botão de download é exibido.
        if st.session_state.pdf_bytes:
            st.download_button(
                label="Clique aqui para Baixar o PDF",
                data=st.session_state.pdf_bytes,
                file_name=f"Relatorio_Enade_2023_{curso}_{municipio}.pdf",
                mime="application/pdf"
            )

    else:
        # Mensagem de aviso se os dados ainda não estiverem prontos
        st.warning(
            "Ainda faltam dados para gerar o relatório completo. Por favor, siga os passos:\n"
            "1. Navegue até a página **'📊 Conhecimento Específico'** e gere uma análise.\n"
            "2. Navegue até a página **'📝 Questionário do Estudante'** e gere uma análise."
        )