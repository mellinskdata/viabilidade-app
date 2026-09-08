"""
reports.py
-----------
Geracao do relatorio executivo em PDF (ReportLab) a partir do dicionario
de resultados produzido por core.executar_analise.

O modulo foi escrito para nunca lancar excecao por chave ausente: todo
acesso ao dicionario de resultados passa por utils.obter, com valores
padrao, entao um resultado parcial ainda gera um PDF utilizavel (com
"N/D" nos campos que nao puderam ser calculados).
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils import formatar_meses, formatar_moeda, formatar_percentual, obter


COR_PRIMARIA = colors.HexColor("#1F2937")
COR_SECUNDARIA = colors.HexColor("#F3F4F6")
COR_TEXTO_CLARO = colors.white


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "TituloRelatorio",
            parent=base["Title"],
            fontSize=18,
            textColor=COR_PRIMARIA,
            spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "Subtitulo",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=16,
        ),
        "secao": ParagraphStyle(
            "Secao",
            parent=base["Heading2"],
            fontSize=13,
            textColor=COR_PRIMARIA,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "corpo": ParagraphStyle(
            "Corpo",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
        ),
        "rodape": ParagraphStyle(
            "Rodape",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
        ),
        "veredito_titulo": ParagraphStyle(
            "VereditoTitulo",
            parent=base["Heading2"],
            fontSize=14,
            alignment=TA_CENTER,
            textColor=COR_TEXTO_CLARO,
        ),
    }


def _cor_severidade(severidade: str):
    mapa = {
        "positivo": colors.HexColor("#1B5E20"),
        "atencao": colors.HexColor("#E65100"),
        "negativo": colors.HexColor("#B71C1C"),
    }
    return mapa.get(severidade, colors.HexColor("#424242"))


def _tabela_padrao(dados, largura_colunas=None) -> Table:
    tabela = Table(dados, colWidths=largura_colunas, hAlign="LEFT")
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
                ("TEXTCOLOR", (0, 0), (-1, 0), COR_TEXTO_CLARO),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_SECUNDARIA]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tabela


def gerar_relatorio_pdf(resultado: dict) -> io.BytesIO:
    """
    Gera o relatorio executivo em PDF e retorna um buffer BytesIO pronto
    para ser oferecido em um st.download_button.

    Nunca lanca excecao por chave ausente: campos que nao existirem no
    dicionario de resultado sao exibidos como "N/D" no PDF.
    """
    resultado = resultado or {}
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        title="Relatorio de Viabilidade Financeira",
    )
    estilos = _estilos()
    elementos = []

    nome_projeto = obter(resultado, "nome_projeto", "Projeto sem nome")
    tipo_projeto = obter(resultado, "tipo_projeto", "Nao informado")

    elementos.append(Paragraph(f"Relatorio de Viabilidade - {nome_projeto}", estilos["titulo"]))
    elementos.append(
        Paragraph(
            f"Tipo de projeto: {tipo_projeto} | Gerado em "
            f"{datetime.now().strftime('%d/%m/%Y as %H:%M')}",
            estilos["subtitulo"],
        )
    )

    # ------------------------------------------------------------------
    # Parametros do projeto
    # ------------------------------------------------------------------
    elementos.append(Paragraph("Parametros do Projeto", estilos["secao"]))
    dados_parametros = [
        ["Parametro", "Valor"],
        ["Periodo de analise", f"{obter(resultado, 'periodo_meses', 'N/D')} meses"],
        ["TMA (ao ano)", formatar_percentual(obter(resultado, "tma_anual"))],
        ["Investimento inicial", formatar_moeda(obter(resultado, "investimento_inicial"))],
        ["Pro-labore desejado / mes", formatar_moeda(obter(resultado, "pro_labore"))],
        [
            "Modo de fluxo de caixa",
            "Media mensal" if obter(resultado, "modo_fluxo") == "media" else "Lancamentos mensais",
        ],
    ]
    elementos.append(_tabela_padrao(dados_parametros, largura_colunas=[7 * cm, 9 * cm]))

    # ------------------------------------------------------------------
    # Indicadores financeiros
    # ------------------------------------------------------------------
    elementos.append(Paragraph("Indicadores Financeiros", estilos["secao"]))
    dados_indicadores = [
        ["Indicador", "Valor"],
        ["VPL (Valor Presente Liquido)", formatar_moeda(obter(resultado, "vpl"))],
        ["TIR mensal", formatar_percentual(obter(resultado, "tir_mensal"))],
        ["TIR anual", formatar_percentual(obter(resultado, "tir_anual"))],
        ["TIRM mensal", formatar_percentual(obter(resultado, "tirm_mensal"))],
        ["TIRM anual", formatar_percentual(obter(resultado, "tirm_anual"))],
        ["Payback simples", formatar_meses(obter(resultado, "payback_simples_meses"))],
        ["Payback descontado", formatar_meses(obter(resultado, "payback_descontado_meses"))],
    ]
    elementos.append(_tabela_padrao(dados_indicadores, largura_colunas=[9 * cm, 7 * cm]))

    # ------------------------------------------------------------------
    # Analise de risco
    # ------------------------------------------------------------------
    elementos.append(Paragraph("Analise de Risco (Sensibilidade da TIR)", estilos["secao"]))
    sensibilidade = obter(resultado, "sensibilidade", {}) or {}
    inclinacao_tir = obter(sensibilidade, "inclinacao_tir", None)
    dados_risco = [
        ["Indicador", "Valor"],
        ["Classificacao de risco", obter(resultado, "risco", "N/D")],
        [
            "Inclinacao da reta (TIR mensal x variacao de receita)",
            f"{inclinacao_tir:.2f} p.p. por 1% de variacao" if inclinacao_tir is not None else "N/D",
        ],
    ]
    elementos.append(_tabela_padrao(dados_risco, largura_colunas=[9 * cm, 7 * cm]))
    elementos.append(Spacer(1, 6))
    elementos.append(
        Paragraph(
            "A inclinacao mede o quanto a TIR mensal se altera, em pontos "
            "percentuais, para cada 1% de variacao (positiva ou negativa) na "
            "receita projetada, mantendo custos e pro-labore constantes. "
            "Quanto maior o modulo da inclinacao, maior a sensibilidade do "
            "projeto a erros de previsao de receita e, portanto, maior o "
            "risco.",
            estilos["corpo"],
        )
    )

    # ------------------------------------------------------------------
    # Veredito
    # ------------------------------------------------------------------
    elementos.append(Spacer(1, 16))
    veredito = obter(resultado, "veredito", {}) or {}
    titulo_veredito = obter(veredito, "titulo", "Veredito nao disponivel")
    severidade = obter(veredito, "severidade", "neutro")
    justificativa = obter(
        veredito, "justificativa", "Nao foi possivel gerar a justificativa do veredito."
    )

    tabela_veredito = Table(
        [[Paragraph(titulo_veredito, estilos["veredito_titulo"])]],
        colWidths=[16 * cm],
    )
    tabela_veredito.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _cor_severidade(severidade)),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elementos.append(tabela_veredito)
    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph(justificativa, estilos["corpo"]))

    elementos.append(Spacer(1, 20))
    elementos.append(
        Paragraph(
            "Relatorio gerado automaticamente. Os resultados dependem "
            "integralmente das premissas informadas e nao substituem uma "
            "analise financeira profissional detalhada.",
            estilos["rodape"],
        )
    )

    doc.build(elementos)
    buffer.seek(0)
    return buffer
