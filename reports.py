from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import matplotlib.pyplot as plt
import io
import numpy as np
from utils import format_brl, format_pct

def generate_pdf_buffer(results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle(name='H2', parent=styles['Heading2'], spaceBefore=15, spaceAfter=10)
    normal = styles['Normal']
    
    elements = []
    
    elements.append(Paragraph(f"Relatório de Viabilidade Econômica", title_style))
    elements.append(Paragraph(f"<b>Projeto:</b> {results['nome']}", normal))
    elements.append(Paragraph(f"<b>Tipo:</b> {results['tipo']}", normal))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("1. VEREDITO FINAL", h2_style))
    elements.append(Paragraph(f"<b>Resultado:</b> {results['veredito']} (Score: {results['score']}/100)", normal))
    for c in results['criterios']:
        elements.append(Paragraph(f"{c[0]} {c[1]}", normal))
    
    elements.append(Paragraph("2. INDICADORES FINANCEIROS", h2_style))
    base = results['base']
    
    data_ind = [
        ["Indicador", "Valor"],
        ["VPL (Valor Presente Líquido)", format_brl(base['vpl'])],
        ["TIR Mensal", format_pct(base['tir_m'])],
        ["TIR Anual", format_pct(base['tir_a'])],
        ["Payback Descontado", f"{base['payback']:.1f} meses" if base['payback'] else "Não recupera"]
    ]
    t_ind = Table(data_ind, colWidths=[200, 200])
    t_ind.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#ecf0f1")),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elements.append(t_ind)
    
    elements.append(Paragraph("3. AVALIAÇÃO DE RISCO", h2_style))
    elements.append(Paragraph(f"<b>Classificação de Risco:</b> {results['risco_classificacao']}", normal))
    lim = format_pct(results['limite_viabilidade']) if results['limite_viabilidade'] else "N/A"
    elements.append(Paragraph(f"<b>Queda limite suportada nas vendas:</b> {lim}", normal))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
