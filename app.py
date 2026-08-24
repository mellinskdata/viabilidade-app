import streamlit as st
from core import ProjectAnalyzer
from reports import generate_pdf_buffer

st.set_page_config(page_title="Análise de Viabilidade Financeira", layout="wide")

st.title("Análise de Viabilidade de Projetos")

st.sidebar.header("Parâmetros do Projeto")
nome_projeto = st.sidebar.text_input("Nome do Projeto", "Cafeteria")
tipo_projeto = st.sidebar.selectbox("Tipo de Projeto", ["Futuro", "Existente"])

investimento = st.sidebar.number_input("Investimento Inicial (R$)", min_value=0.0, value=80000.0, step=1000.0)
tma_anual = st.sidebar.number_input("TMA Anual (%)", min_value=0.0, value=12.0, step=0.5) / 100.0
pro_labore = st.sidebar.number_input("Pró-Labore / Custos Fixos Extra (R$)", min_value=0.0, value=0.0, step=100.0)

mode = st.sidebar.radio("Modo de Entrada", ["Média Mensal", "Lançamentos Mensais"])

if mode == "Média Mensal":
    periodo_meses = st.sidebar.number_input("Período (Meses)", min_value=1, value=36, step=1)
    receita_media = st.sidebar.number_input("Receita Média Mensal (R$)", min_value=0.0, value=10000.0, step=500.0)
    custo_medio = st.sidebar.number_input("Custo Médio Mensal (R$)", min_value=0.0, value=5000.0, step=500.0)
    
    data_input = {
        "nome": nome_projeto,
        "tipo": tipo_projeto,
        "mode": "average",
        "investimento": investimento,
        "tma_anual": tma_anual,
        "pro_labore": pro_labore,
        "periodo_meses": periodo_meses,
        "receita_media": receita_media,
        "custo_medio": custo_medio
    }
else:
    st.sidebar.info("Preencha os lançamentos mensais no painel central.")
    data_input = {
        "nome": nome_projeto,
        "tipo": tipo_projeto,
        "mode": "custom",
        "investimento": investimento,
        "tma_anual": tma_anual,
        "pro_labore": pro_labore,
        "dados_mensais": []
    }

analyzer = ProjectAnalyzer(data_input)
res = analyzer.analyze()

st.subheader("Indicadores Financeiros Principais")

base = res['base']

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("VPL", f"R$ {base['vpl']:,.2f}")
    st.metric("TIR Mensal", f"{base['tir_m']*100:.2f}%" if base['tir_m'] is not None else "-")
    st.metric("TIR Anual", f"{base['tir_a']*100:.2f}%" if base['tir_a'] is not None else "-")

with col2:
    st.metric("TIRM Mensal", f"{base['tirm_m']*100:.2f}%" if base['tirm_m'] is not None else "-")
    st.metric("Payback Simples", f"{base['payback']:.1f} meses" if base['payback'] is not None else "Não atinge")
    st.metric("Payback Descontado", f"{base['payback_desc']:.1f} meses" if base['payback_desc'] is not None else "Não atinge")

with col3:
    st.metric("Queda Limite (Vendas)", f"{res['limite_viabilidade']*100:.1f}%")
    st.metric("Ângulo de Risco", f"{res['risco_angulo']:.2f}°")

with col4:
    st.metric("Classificação de Risco", res['risco_classificacao'])
    st.metric("Veredito", res['veredito'])

st.divider()

st.subheader("Relatório de Exportação")
pdf_buffer = generate_pdf_buffer(res)

st.download_button(
    label="Baixar Relatório em PDF",
    data=pdf_buffer,
    file_name=f"relatorio_{nome_projeto.lower().replace(' ', '_')}.pdf",
    mime="application/pdf"
)
