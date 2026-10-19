"""Exportação do resultado completo com apenas o payback descontado."""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from utils import format_brl, format_pct


def generate_pdf_buffer(results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="ProjectTitle", parent=styles["Heading1"], alignment=1, spaceAfter=20)
    section_style = ParagraphStyle(name="ProjectSection", parent=styles["Heading2"], spaceBefore=15, spaceAfter=10)
    normal = styles["Normal"]

    elements = [
        Paragraph("Relatório de Viabilidade Econômica", title_style),
        Paragraph(f"<b>Projeto:</b> {escape(str(results['nome']))}", normal),
        Spacer(1, 15),
        Paragraph("1. VEREDITO FINAL", section_style),
        Paragraph(f"<b>Resultado:</b> {results['veredito']} (Score Geral: {results['score']}/100)", normal),
    ]
    for status, desc in results["criterios"]:
        elements.append(Paragraph(f"{escape(status)} {escape(desc)}", normal))

    elements.append(Paragraph("2. INDICADORES FINANCEIROS", section_style))
    base = results["base"]
    payback = base["payback_descontado"]
    indicators = [
        ["Indicador", "Valor calculado"],
        ["VPL", format_brl(base["vpl"])],
        ["TIR Anual", format_pct(base["tir_a"])],
        ["TIRM Anual", format_pct(base["tirm_a"])],
        ["Payback Descontado", f"{payback:.1f} meses" if payback is not None else "Não recupera"],
    ]
    indicator_table = Table(indicators, colWidths=[245, 230], repeatRows=1)
    indicator_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))
    elements.append(indicator_table)

    elements.append(Paragraph("3. ANÁLISE DE RISCO E SENSIBILIDADE", section_style))
    if results["risco_angulo"] is not None:
        risk_text = f"<b>Classificação:</b> {escape(results['risco_classificacao'])} (ângulo de sensibilidade: {results['risco_angulo']:.1f} graus)"
    else:
        risk_text = "<b>Classificação de risco:</b> Indefinido"
    elements.append(Paragraph(risk_text, normal))
    limit = results["limite_viabilidade"]
    if limit is not None and base["vpl"] > 0:
        elements.append(Paragraph(f"<b>Limite de queda de receitas até VPL zero:</b> {format_pct(limit)}", normal))
    elements.append(Paragraph("O ângulo é um índice simplificado de sensibilidade e não mede a probabilidade de prejuízo.", normal))

    elements.append(Paragraph("4. RECEITAS E CUSTOS MÊS A MÊS", section_style))
    month_rows = [["Mês", "Receita", "Custo", "Fluxo líquido"]]
    for idx, month in enumerate(results["dados_mensais"], start=1):
        revenue, cost = month["receita"], month["custo"]
        month_rows.append([str(idx), format_brl(revenue), format_brl(cost), format_brl(revenue - cost)])
    months_table = Table(month_rows, colWidths=[42, 144, 144, 145], repeatRows=1, hAlign="LEFT")
    months_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf2f7")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(months_table)
    doc.build(elements)
    buffer.seek(0)
    return buffer