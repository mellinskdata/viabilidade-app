from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def format_pct(val):
    if val is None:
        return "-"
    return f"{val * 100:.2f}%"

def generate_pdf_buffer(res: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1E3A8A"))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor("#1E3A8A"))
    normal_style = styles['Normal']

    story.append(Paragraph(f"Relatório de Análise de Viabilidade: {res.get('nome', 'Projeto')}", title_style))
    story.append(Spacer(1, 12))

    base = res['base']
    dados_tabela = [
        ["Indicador", "Valor"],
        ["VPL", f"R$ {base['vpl']:,.2f}"],
        ["TIR Mensal", format_pct(base['tir_m'])],
        ["TIR Anual", format_pct(base['tir_a'])],
        ["TIRM Mensal", format_pct(base['tirm_m'])],
        ["Payback Simples", f"{base['payback']:.1f} meses" if base['payback'] is not None else "Não atinge"],
        ["Payback Descontado", f"{base['payback_desc']:.1f} meses" if base['payback_desc'] is not None else "Não atinge"],
        ["Queda Limite Suportada", format_pct(res['limite_viabilidade'])],
        ["Ângulo de Sensibilidade", f"{res['risco_angulo']:.2f}°"],
        ["Risco", res['risco_classificacao']],
        ["Score", f"{res['score']}/100"],
        ["Veredito", res['veredito']]
    ]

    t = Table(dados_tabela, colWidths=[200, 250])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F3F4F6")),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#D1D5DB")),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 16))
    
    story.append(Paragraph("Critérios de Avaliação:", h2_style))
    story.append(Spacer(1, 6))
    for c in res.get('criterios', []):
        story.append(Paragraph(f"• {c}", normal_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
