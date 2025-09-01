import os
import tempfile
import pandas as pd
import streamlit as st
from fpdf import FPDF
from PyPDF2 import PdfWriter

from analysis import (
    plot_performance_graph,
    plot_average_graph,
    plot_count_graph,
    show_best_hei_ranking_table,
)

# =========================================================
# TABELA -> imprime linhas com mesma altura e bordas contínuas
# =========================================================
def add_dataframe_to_pdf(pdf: FPDF, df: pd.DataFrame) -> None:
    """
    Desenha um DataFrame no PDF com a tabela centralizada na página, usando medição real
    de quebra de texto (split_only=True) para Tema e IES, e bordas contínuas.
    """
    # Larguras (somam 169mm -> cabe no miolo da página A4 com margens padrão)
    col_widths = {
        "Tema": 50,
        "IES com o melhor desempenho": 50,
        "Nº de participantes": 25,
        "Melhor (%)": 22,
        "UFPA (%)": 22,
    }

    # Alturas base
    pdf.set_font("Times", "B", 8)
    header_h = pdf.font_size * 2.0
    line_h = pdf.font_size * 1.6  # altura de cada sublinha dentro de uma célula multilinha

    # --- ALTERAÇÃO PARA CENTRALIZAR ---
    # 1. Calcula a largura total da tabela somando as larguras das colunas.
    total_width = sum(col_widths.values())
    
    # 2. Calcula a posição X inicial para a tabela ficar centralizada na página.
    table_x = (pdf.w - total_width) / 2

    # 3. Move o cursor para essa posição inicial ANTES de desenhar o cabeçalho.
    pdf.set_x(table_x)
    # --- FIM DA ALTERAÇÃO ---

    # Cabeçalho
    for col_name in df.columns:
        pdf.cell(col_widths.get(col_name, 20), header_h, col_name, border=1, align="C")
    pdf.ln(header_h)

    # Corpo
    pdf.set_font("Times", "", 7)

    for _, row in df.iterrows():
        # A variável 'x' agora começa na posição centralizada calculada
        x = table_x
        y = pdf.get_y()

        tema_txt = f" {str(row['Tema'])}"
        ies_txt = f" {str(row['IES com o melhor desempenho'])}"
        n_txt = f"{str(row['Nº de participantes'])}"
        mel_txt = f"{str(row['Melhor (%)'])}"
        ufpa_txt = f"{str(row['UFPA (%)'])}"

        # Mede quantas linhas cada multilinha vai ocupar (sem desenhar)
        tema_lines = pdf.multi_cell(
            col_widths["Tema"], line_h, tema_txt, border=0, align="L", split_only=True
        )
        ies_lines = pdf.multi_cell(
            col_widths["IES com o melhor desempenho"],
            line_h,
            ies_txt,
            border=0,
            align="L",
            split_only=True,
        )

        row_lines = max(len(tema_lines), len(ies_lines), 1)
        row_h = row_lines * line_h

        # Evita cortar a linha na quebra de página
        if y + row_h > (pdf.h - pdf.b_margin):
            pdf.add_page()
            # Garante que a posição X seja resetada para o centro na nova página
            pdf.set_x(table_x)
            x = table_x
            y = pdf.get_y()

        # --- Tema (desenha retângulo de borda inteira + texto dentro)
        pdf.rect(x, y, col_widths["Tema"], row_h)
        pdf.set_xy(x, y)
        pdf.multi_cell(col_widths["Tema"], line_h, tema_txt, border=0, align="L")
        x += col_widths["Tema"]

        # --- IES (mesma lógica)
        pdf.set_xy(x, y) # Define a posição para a próxima célula
        pdf.rect(x, y, col_widths["IES com o melhor desempenho"], row_h)
        pdf.multi_cell(
            col_widths["IES com o melhor desempenho"],
            line_h,
            ies_txt,
            border=0,
            align="L",
        )
        x += col_widths["IES com o melhor desempenho"]

        # --- Nº participantes
        pdf.set_xy(x, y) # Define a posição para a próxima célula
        pdf.rect(x, y, col_widths["Nº de participantes"], row_h)
        pdf.cell(col_widths["Nº de participantes"], row_h, n_txt, border=0, align="C")
        x += col_widths["Nº de participantes"]

        # --- Melhor (%)
        pdf.set_xy(x, y) # Define a posição para a próxima célula
        pdf.rect(x, y, col_widths["Melhor (%)"], row_h)
        pdf.cell(col_widths["Melhor (%)"], row_h, mel_txt, border=0, align="C")
        x += col_widths["Melhor (%)"]

        # --- UFPA (%)
        pdf.set_xy(x, y) # Define a posição para a próxima célula
        pdf.rect(x, y, col_widths["UFPA (%)"], row_h)
        pdf.cell(col_widths["UFPA (%)"], row_h, ufpa_txt, border=0, align="C")

        # Avança o cursor para a próxima linha, alinhado ao início da tabela
        pdf.set_xy(table_x, y + row_h)


# =========================================================
# RELATÓRIO COMPLETO
# =========================================================
def generate_full_report(
    Enade_2023,
    QE_data_2023,
    COURSE_CODES,
    hei_dict,
    course_code,
    group_code,
    curso_nome,
    municipio_nome,
):
    """
    Centraliza toda a lógica de geração de relatório, incluindo a tabela de ranking.
    Retorna os bytes do PDF final.
    """
    image_paths = {}
    generated_pdf_path = None
    final_path = None

    PRIMARY_BLUE = (19, 81, 180)
    BLACK = (0, 0, 0)
    ANEXO_QE_PATH = "anexo_qe_2023.pdf"
    CAPA_RELATORIO_PATH = "src/file/capa_relatorio.pdf"

    TITLE_REPORT = "Relatório Análise dos Microdados ENADE 2023"
    TITLE_INTRO = "Apresentação"
    INTRO_PARAGRAPHS = [
        "A CPA, em parceria com a DIAVI/PROPLAN, apresenta as análises descritivas dos microdados do Enade 2023, com o objetivo de auxiliar as coordenações de curso na identificação de melhorias a serem implementadas na graduação.",
        "As análises compreendem os temas do Componente Específico da prova do Enade e as questões do Questionário do Estudante, relativas às dimensões Organização Didático-pedagógica, Infraestrutura e Instalações Físicas e Oportunidade Ampliação da Formação Profissional.",
    ]
    TITLE_CE = "Análises Conhecimento Específico"
    CE_PARAGRAPHS = [
        "A análise gráfica fornece informações valiosas a respeito do desempenho dos alunos nas temáticas avaliadas na prova, uma vez que possibilita averiguar se as estratégias pedagógicas aplicadas nas disciplinas ministradas estão produzindo os resultados almejados. São apresentados dois gráficos que exibem a comparação entre o desempenho do curso de graduação da UFPA e o desempenho nacional, calculado a partir do mesmo curso ofertado por todas as IES no país que participam do exame.",
        "O Gráfico da Razão do Percentual de Acerto exibe o desempenho do curso da UFPA em comparação com a média nacional, por tema avaliado no ENADE 2023. A interpretação do gráfico da razão é a seguinte: Razão > 1,0: a UFPA apresentou desempenho superior à média nacional; Razão < 1,0: a UFPA obteve desempenho inferior à média nacional; Razão = 1,0: o desempenho da UFPA foi equivalente à média nacional.",
        "O Gráfico de Percentual de Acerto por Tema apresenta a comparação entre o percentual de acertos do curso da UFPA e o percentual médio nacional, para cada temática do componente específico da prova.",
        "Na Tabela Ranking é apresentada a instituição com melhor percentual de desempenho, por temática do exame, em comparação com o desempenho do curso da UFPA.",
    ]
    TITLE_QE = "Análises Questionário do Estudante"
    QE_PARAGRAPHS = [
        "Para cada questão no Questionário do Estudante, são disponibilizadas 6 alternativas de resposta que indicam o grau de concordância com cada assertiva, em uma escala que varia de 1 (discordância total) a 6 (concordância total), além das alternativas 7 (Não sei responder) e 8 (Não se aplica).",
        "Para cada dimensão do questionário, foram gerados dois gráficos. O gráfico de barras apresenta a média atribuída pelos alunos para cada questão, excluídas as alternativas 7 e 8. São destacadas as questões com a maior e a menor média.",
        "O gráfico de linhas representa, por questão, o total de respostas absolutas (contagem) agrupadas pelo tipo de alternativa escolhida, da seguinte forma: 1-2; 3-4; 5-6; 7-8.",
    ]

    try:
        # --- 1) Gráficos e dados da TABELA ---
        _, image_paths["razao_chart"], _, image_paths["percent_chart"] = plot_performance_graph(
            Enade_2023, COURSE_CODES, group_code, course_code
        )

        ranking_df = show_best_hei_ranking_table(
            Enade_2023, COURSE_CODES, hei_dict, group_code, course_code, public_only=True
        )

        ranking_df_pdf = ranking_df.rename(columns={"Melhor curso (%)": "Melhor (%)"})[
            ["Tema", "IES com o melhor desempenho", "Nº de participantes", "Melhor (%)", "UFPA (%)"]
        ]

        odp_questions = [
            "QE_I27", "QE_I28", "QE_I29", "QE_I30", "QE_I31", "QE_I32", "QE_I33", "QE_I34", "QE_I35",
            "QE_I36", "QE_I37", "QE_I38", "QE_I39", "QE_I40", "QE_I42", "QE_I47", "QE_I48", "QE_I49",
            "QE_I51", "QE_I55", "QE_I57", "QE_I66",
        ]
        infra_questions = [
            "QE_I50", "QE_I54", "QE_I56", "QE_I58", "QE_I59", "QE_I60", "QE_I61", "QE_I62", "QE_I63",
            "QE_I64", "QE_I65", "QE_I67", "QE_I68",
        ]
        oaf_questions = ["QE_I43", "QE_I44", "QE_I45", "QE_I46", "QE_I52", "QE_I53"]

        _, image_paths["odp_img_av"] = plot_average_graph(
            QE_data_2023, course_code, odp_questions, [""] * len(odp_questions)
        )
        _, image_paths["infra_img_av"] = plot_average_graph(
            QE_data_2023, course_code, infra_questions, [""] * len(infra_questions)
        )
        _, image_paths["oaf_img_av"] = plot_average_graph(
            QE_data_2023, course_code, oaf_questions, [""] * len(oaf_questions)
        )
        _, image_paths["odp_img_co"] = plot_count_graph(QE_data_2023, course_code, odp_questions)
        _, image_paths["infra_img_co"] = plot_count_graph(QE_data_2023, course_code, infra_questions)
        _, image_paths["oaf_img_co"] = plot_count_graph(QE_data_2023, course_code, oaf_questions)

        if not all(path for path in image_paths.values()):
            raise ValueError("Falha na geração de uma ou mais imagens para o relatório.")

        # --- 2) Montagem do PDF ---
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)

        # Capa
        pdf.add_page()
        pdf.set_y(100)
        pdf.set_font("Times", "B", 23)
        pdf.multi_cell(0, 10, TITLE_REPORT, align="C")
        pdf.cell(0, 10, f"{curso_nome} - {municipio_nome}", ln=True, align="C")

        # Função de página de texto
        def add_text_page(title, paragraphs):
            pdf.add_page()
            pdf.set_y(40)
            pdf.set_font("Times", "B", 19)
            pdf.set_text_color(*PRIMARY_BLUE)
            pdf.cell(0, 10, title, ln=True, align="L")
            pdf.ln(5)
            pdf.set_font("Times", "", 12)
            pdf.set_text_color(*BLACK)
            for p in paragraphs:
                pdf.multi_cell(w=0, h=6, txt=p, border=0, align="J")
                pdf.ln(2)

        add_text_page(TITLE_INTRO, INTRO_PARAGRAPHS)
        add_text_page(TITLE_CE, CE_PARAGRAPHS)
        
        # Gráfico 1 (Razão)
        pdf.add_page()
        pdf.ln(10)
        pdf.set_font("Times", "B", 12)
        pdf.multi_cell(0, 6, f"Razão do Percentual de Acerto UFPA vs. Brasil\n{curso_nome} em {municipio_nome} por Tema no ENADE 2023", align="C")
        pdf.ln(3)
        pdf.image(image_paths["razao_chart"], x=20, w=170)
        pdf.set_font("Times", size=11)
        pdf.cell(0, 8, "Figura 1: Gráfico Razão do Percentual", ln=True, align="C")

        # Gráfico 2 (Percentual) - Em uma nova página para garantir a formatação
        pdf.add_page()
        pdf.ln(10)
        pdf.set_font("Times", "B", 12)
        pdf.multi_cell(0, 6, f"Percentual de Acerto UFPA vs. Brasil\n{curso_nome} em {municipio_nome} por Tema no ENADE 2023", align="C")
        pdf.ln(3)
        pdf.image(image_paths["percent_chart"], x=20, w=170)
        pdf.set_font("Times", size=11)
        pdf.cell(0, 8, "Figura 2: Gráfico Percentual do Acerto", ln=True, align="C")
        
        # Tabela Ranking
        pdf.add_page()
        pdf.ln(10)
        pdf.set_font("Times", "B", 14)
        pdf.cell(0, 10, "Ranking de IES com Melhor Desempenho por Tema", ln=True, align="C")
        pdf.ln(5)
        add_dataframe_to_pdf(pdf, ranking_df_pdf.head(10))
        pdf.ln(5)
        pdf.set_font("Times", size=11)
        pdf.cell(0, 8, "Figura 3: Tabela de Ranking entre IES", ln=True, align="C")

        # Página de introdução do QE
        add_text_page(TITLE_QE, QE_PARAGRAPHS)

        # --- CORREÇÃO APLICADA AQUI ---
        # Função para páginas de gráficos do QE (versão mais compacta)
        def add_qe_charts_page(title, avg_key, count_key, caption_avg, caption_count, curso_nome, municipio_nome):
            pdf.add_page()
            # Reduzido: Fonte 14, altura 8
            pdf.set_font("Times", "B", 14) 
            pdf.set_text_color(*PRIMARY_BLUE)
            pdf.cell(0, 8, title, ln=True, align="C")
            # Reduzido: Espaçamento
            pdf.ln(3)

            # --- Título e Gráfico de Médias ---
            pdf.set_font("Times", "B", 12)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(0, 5, f"Média das respostas em {curso_nome} - {municipio_nome}", align="C")
            # Reduzido: Espaçamento
            pdf.ln(2)
            pdf.image(image_paths[avg_key], x=30, w=150)
            pdf.set_font("Times", size=11)
            pdf.cell(0, 8, caption_avg, ln=True, align="C")
            # Reduzido: Espaçamento entre gráficos
            pdf.ln(5)

            # --- Título e Gráfico de Contagem ---
            pdf.set_font("Times", "B", 12)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(0, 5, f"Contagem das respostas em {curso_nome} - {municipio_nome}", align="C")
            # Reduzido: Espaçamento
            pdf.ln(2)
            pdf.image(image_paths[count_key], x=30, w=150)
            pdf.set_font("Times", size=11)
            pdf.cell(0, 8, caption_count, ln=True, align="C")

        add_qe_charts_page(
            "Organização Didático Pedagógica", "odp_img_av", "odp_img_co",
            "Figura 4: Gráfico de Médias Organização Didático-Pedagógica",
            "Figura 5: Gráfico de Linhas Organização Didático-Pedagógica",
            curso_nome, municipio_nome
        )
        add_qe_charts_page(
            "Infraestrutura e Instalações Físicas", "infra_img_av", "infra_img_co",
            "Figura 6: Gráfico de Médias Infraestrutura",
            "Figura 7: Gráfico de Linhas Infraestrutura",
            curso_nome, municipio_nome
        )
        add_qe_charts_page(
            "Oportunidades de Ampliação da Formação", "oaf_img_av", "oaf_img_co",
            "Figura 8: Gráfico de Médias Ampliação da Formação",
            "Figura 9: Gráfico de Linhas Ampliação da Formação",
            curso_nome, municipio_nome
        )

        # Seção Anexo
        pdf.add_page()
        pdf.set_y(40)
        pdf.set_font("Times", "B", 19)
        pdf.set_text_color(*PRIMARY_BLUE)
        pdf.cell(0, 10, "Anexo Questionário do Estudante", ln=True, align="L")

        # --- 3) Junta capa + miolo + anexo em um PDF final ---
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            generated_pdf_path = tmp_pdf.name
            pdf.output(generated_pdf_path)

        writer = PdfWriter()
        if os.path.exists(CAPA_RELATORIO_PATH):
            with open(CAPA_RELATORIO_PATH, "rb") as f:
                writer.append(f)
        
        with open(generated_pdf_path, "rb") as f:
            writer.append(f)

        if os.path.exists(ANEXO_QE_PATH):
            with open(ANEXO_QE_PATH, "rb") as f:
                writer.append(f)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as final_pdf_file:
            final_path = final_pdf_file.name
            writer.write(final_path)

        with open(final_path, "rb") as f:
            pdf_bytes = f.read()
        return pdf_bytes

    except (FileNotFoundError, ValueError) as e:
        st.error(f"Erro ao gerar o relatório: {e}")
        return None
    finally:
        # Limpeza de arquivos temporários/imagens
        for path in image_paths.values():
            if path and os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
        if generated_pdf_path and os.path.exists(generated_pdf_path):
            try: os.remove(generated_pdf_path)
            except Exception: pass
        if final_path and os.path.exists(final_path):
            try: os.remove(final_path)
            except Exception: pass