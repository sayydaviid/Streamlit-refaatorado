from pathlib import Path
import base64
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

from utils import atualiza_cursos
from pdf_generator import generate_full_report

REPORT_SHORT_DESC = (
    "**O que este relatório traz**: análises dos microdados do Enade 2023. "
    "Compara o desempenho do curso da UFPA com a média nacional por tema do componente específico "
    "(razão > 1 indica desempenho superior), mostra a IES com melhor resultado em cada temática e "
    "apresenta indicadores do Questionário do Estudante — médias por questão nas dimensões "
    "Organização Didático-Pedagógica, Infraestrutura e Oportunidades de Ampliação da Formação, "
    "além da distribuição das respostas."
)

def _inject_css():
    # ../style/style.css relativo a paginas/relatorio.py
    css_path = Path(__file__).resolve().parent.parent / "style" / "style.css"
    if not css_path.exists():
        st.error(f"CSS não encontrado em: {css_path}")
        return
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def show_page(Enade_2023, QE_data_2023, UFPA_data, COURSE_CODES, hei_dict):
    # ---------- CSS externo ----------
    _inject_css()

    # ---------- TÍTULO + DESCRIÇÃO ----------
    st.title("📥 Gerar e Baixar Relatório Completo")
    st.markdown(REPORT_SHORT_DESC)

    # ---------- ESTADO ----------
    ss = st.session_state
    ss.setdefault("pdf_report_bytes", None)
    ss.setdefault("municipio_relatorio_op", None)
    ss.setdefault("curso_relatorio_op", None)
    ss.setdefault("ultima_chave_relatorio", None)
    ss.setdefault("_prev_municipio", None)

    # ---------- INSTRUÇÃO ----------
    st.markdown(
        '<p class="helper-text">Selecione o município e o curso. O relatório será gerado automaticamente quando ambas as opções forem escolhidas.</p>',
        unsafe_allow_html=True,
    )

    # ---------- SELECTS ----------
    col1, col2 = st.columns(2, gap="small")
    municipios = sorted(UFPA_data["NOME_MUNIC_CURSO"].unique().tolist())

    with col1:
        municipio_sel = st.selectbox(
            "Município",
            options=municipios,
            index=None,
            placeholder="Escolha um município…",
            key="municipio_relatorio_op",
        )

    cursos_disponiveis = atualiza_cursos(UFPA_data, municipio_sel) if municipio_sel else []

    # reset ao trocar município
    if municipio_sel != ss.get("_prev_municipio"):
        ss["_prev_municipio"] = municipio_sel
        ss["curso_relatorio_op"] = None
        ss["pdf_report_bytes"] = None
        ss["ultima_chave_relatorio"] = None

    with col2:
        curso_sel = st.selectbox(
            "Curso",
            options=cursos_disponiveis,
            index=None,
            placeholder="Escolha um curso…",
            key="curso_relatorio_op",
        )

    status_ph = st.empty()

    # ---------- GERAÇÃO ----------
    def tentar_gerar_relatorio():
        muni = ss.get("municipio_relatorio_op")
        curso = ss.get("curso_relatorio_op")

        if not muni or not curso:
            ss["pdf_report_bytes"] = None
            ss["ultima_chave_relatorio"] = None
            status_ph.empty()
            return

        # localizar course_code e group_code
        course_code = None
        group_code = None
        for code, details in COURSE_CODES.items():
            if details[1] == curso and details[3] == muni:
                course_code = code
                group_code = details[0]
                break

        if not course_code or not group_code:
            status_ph.warning("Não foi possível localizar os códigos para a seleção atual.")
            ss["pdf_report_bytes"] = None
            ss["ultima_chave_relatorio"] = None
            return

        chave = f"{muni}|{curso}"
        if ss.get("ultima_chave_relatorio") == chave and ss.get("pdf_report_bytes"):
            return

        # loader
        status_ph.markdown(
            '<div class="loader-wrap">'
            '<span class="lds-ring"><div></div><div></div><div></div><div></div></span>'
            '<span>Gerando relatório em PDF…</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        pdf_bytes = generate_full_report(
            Enade_2023, QE_data_2023, COURSE_CODES, hei_dict,
            course_code, group_code, curso, muni
        )

        if pdf_bytes:
            ss["pdf_report_bytes"] = pdf_bytes
            ss["ultima_chave_relatorio"] = chave
            status_ph.empty()   # não mostra "sucesso"
        else:
            ss["pdf_report_bytes"] = None
            ss["ultima_chave_relatorio"] = None
            status_ph.error("Falha ao gerar o relatório. Tente novamente.")

    tentar_gerar_relatorio()

    # ---------- PRÉVIA + DOWNLOAD ----------
    if ss.pdf_report_bytes:
        hdr_l, hdr_r = st.columns([1, 0.22], gap="small")
        with hdr_l:
            st.markdown('<h4 class="h4-tight">Pré-visualização do Relatório</h4>', unsafe_allow_html=True)
        with hdr_r:
            # Botão HTML (texto sempre branco)
            b64 = base64.b64encode(ss.pdf_report_bytes).decode()
            file_name = f"Relatorio_Enade_2023_{ss['curso_relatorio_op']}_{ss['municipio_relatorio_op']}.pdf"
            btn_html = f"""
            <div class="inline-dl">
              <a class="dl-btn" href="data:application/pdf;base64,{b64}" download="{file_name}" title="Baixar PDF">
                Baixar PDF
              </a>
            </div>
            """
            st.markdown(btn_html, unsafe_allow_html=True)

        # Viewer sem rolagem horizontal
        st.markdown('<div class="no-x-scroll">', unsafe_allow_html=True)
        pdf_viewer(input=ss.pdf_report_bytes, height=680)
        st.markdown('</div>', unsafe_allow_html=True)
