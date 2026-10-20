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
    section_style = ParagraphStyle(name="ProjectSection", parent=styles["Heading2"], spaceBefore=15, spaceAfter=10, keepWithNext=True)
    normal = styles["Normal"]
    help_style = ParagraphStyle(
        name="IndicatorHelpText", parent=normal, spaceBefore=5, spaceAfter=8, leading=14
    )

    # O PDF tem navegação interna em vez de modais: '?' leva ao glossário.
    def indicador_com_ajuda(rotulo, chave):
        return Paragraph(
            f'{escape(rotulo)} <link href="#ajuda_{chave}" color="#1d4ed8"><u>?</u></link>', normal
        )

    base = results["base"]
    elements = [
        Paragraph("Relatório de Viabilidade Econômica", title_style),
        Paragraph(f"<b>Projeto:</b> {escape(str(results['nome']))}", normal),
        Paragraph(f"<b>Investimento inicial:</b> {escape(format_brl(-base['cfs'][0]))}", normal),
        Paragraph(f"<b>Período analisado:</b> {len(results['dados_mensais'])} meses", normal),
        Spacer(1, 15),
        Paragraph("1. VEREDITO FINAL", section_style),
        Paragraph(f"<b>Resultado:</b> {results['veredito']} (Score Geral: {results['score']}/100)", normal),
    ]
    for status, desc in results["criterios"]:
        elements.append(Paragraph(f"{escape(status)} {escape(desc)}", normal))

    elements.append(Paragraph("2. INDICADORES FINANCEIROS", section_style))
    payback = base["payback_descontado"]
    indicators = [
        ["Indicador", "Valor calculado"],
        [indicador_com_ajuda("TMA anual", "tma"), format_pct(base["tma_a"])],
        [indicador_com_ajuda("VPL", "vpl"), format_brl(base["vpl"])],
        [indicador_com_ajuda("TIR mensal", "tir"), format_pct(base["tir_m"])],
        [indicador_com_ajuda("TIR anual", "tir"), format_pct(base["tir_a"])],
        [indicador_com_ajuda("TIRM mensal", "tirm"), format_pct(base["tirm_m"])],
        [indicador_com_ajuda("TIRM anual", "tirm"), format_pct(base["tirm_a"])],
        [indicador_com_ajuda("Payback Descontado", "payback"),
         f"{payback:.2f}".replace(".", ",") + " meses" if payback is not None else "Não recupera"],
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

    elements.append(Paragraph('3. ANÁLISE DE RISCO E SENSIBILIDADE <link href="#ajuda_risco" color="#1d4ed8"><u>?</u></link>', section_style))
    if results["risco_classificacao"] != "INDEFINIDO":
        risk_text = f"<b>Classificação:</b> {escape(results['risco_classificacao'])}"
    else:
        risk_text = "<b>Classificação de risco:</b> Indefinido"
    elements.append(Paragraph(risk_text, normal))
    limit = results["limite_viabilidade"]
    if limit is not None and base["vpl"] > 0:
        elements.append(Paragraph(f"<b>Limite de queda de receitas até VPL zero:</b> {format_pct(limit)}", normal))
    elements.append(Paragraph("4. GUIA DOS INDICADORES (?): CLIQUE NO SÍMBOLO NA TABELA", section_style))
    glossario = [
        ("tma", "TMA", "Taxa mínima de rentabilidade exigida pelo investidor; serve como taxa de desconto para trazer valores futuros ao presente."),
        ("vpl", "VPL", "Valor presente das entradas e saídas de caixa do projeto, descontadas pela TMA. VPL positivo indica criação de valor."),
        ("tir", "TIR", "Taxa que torna o VPL igual a zero. A taxa mensal é calculada com os fluxos mensais; a taxa anual é a equivalente composta."),
        ("tirm", "TIRM", "Taxa modificada que considera taxas realistas para financiar saídas e reinvestir entradas. O valor anual equivale à capitalização do mensal."),
        ("payback", "Payback Descontado", "Tempo estimado para recuperar o investimento inicial, considerando os fluxos de caixa descontados pela TMA."),
        ("risco", "Sensibilidade da TIR", "Avalia como mudanças nas receitas poderiam afetar a rentabilidade do projeto. É uma análise de cenários, não uma probabilidade de prejuízo."),
        ("custos", "Custos", "Despesas da operação, como matéria-prima, energia, água, gás, internet e impostos. Os valores representam os custos previstos para cada mês."),
    ]
    for chave, rotulo, explicacao in glossario:
        elements.append(Paragraph(
            f'<a name="ajuda_{chave}"/><b>{escape(rotulo)}:</b> {escape(explicacao)}',
            help_style,
        ))

    elements.append(Paragraph("5. RECEITAS E CUSTOS MÊS A MÊS", section_style))
    month_rows = [["Mês", "Receita", indicador_com_ajuda("Custo", "custos"), "Fluxo líquido"]]
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