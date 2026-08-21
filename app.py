import streamlit as st
import pandas as pd
from utils import parse_brl, format_brl, format_pct
from core import ProjectAnalyzer
from reports import generate_pdf_buffer

st.set_page_config(page_title="Viabilidade Econômica", page_icon="📈", layout="centered")

st.markdown("""
    <style>
    .aprovado {color: #2ecc71; font-weight: bold; font-size: 28px;}
    .reprovado {color: #e74c3c; font-weight: bold; font-size: 28px;}
    .revisao {color: #f1c40f; font-weight: bold; font-size: 28px;}
    </style>
""", unsafe_allow_html=True)

if "ex_nome" not in st.session_state:
    st.session_state.update({
        "ex_nome": "", "ex_tma": "", "ex_pro": "", "ex_inv": "", 
        "ex_rec": "", "ex_cus": "", "ex_meses": "12"
    })

def carregar_exemplo():
    st.session_state.update({
        "ex_nome": "Trailer de Sukiyaki (Exemplo)", "ex_tma": "15,00", "ex_pro": "2.000,00", 
        "ex_inv": "29.400,00", "ex_rec": "10.000,00", "ex_cus": "4.000,00", "ex_meses": "12"
    })

with st.sidebar:
    st.title("Ajuda e Conceitos")
    st.button("Carregar Dados de Exemplo", on_click=carregar_exemplo, use_container_width=True)
    
    with st.expander("O que significam as siglas?"):
        st.write("**VPL:** Valor Presente Líquido. Indica se o negócio gera valor acima da taxa mínima exigida.")
        st.write("**TIR:** Taxa Interna de Retorno. Mede a rentabilidade mensal do negócio.")
        st.write("**Payback:** Tempo necessário para recuperar o investimento inicial.")

st.title("Análise de Viabilidade Econômica")
st.write("Ferramenta técnica de apoio à decisão em pequenos empreendimentos.")

st.header("1. Dados Básicos")
col1, col2 = st.columns(2)
nome = col1.text_input("Nome do Negócio", value=st.session_state.ex_nome)
tipo = col2.radio("Situação", ["Negócio Futuro", "Negócio Existente"])

col3, col4 = st.columns(2)
tma = col3.text_input("Taxa Mínima Aceitável ao ano (%)", value=st.session_state.ex_tma)
pro_labore = col4.text_input("Pró-Labore mensal desejado (R$)", value=st.session_state.ex_pro)

st.header("2. Receitas e Custos")
modo = st.radio("Forma de preenchimento", ["Usar Média Mensal", "Preencher Mês a Mês"])
inv = st.text_input("Investimento Inicial (R$)", value=st.session_state.ex_inv)

dados_mensais = []
periodo_meses = 0
rec_media = 0
cus_medio = 0

if "Média" in modo:
    col5, col6, col7 = st.columns(3)
    rec_media_txt = col5.text_input("Receita Média mensal (R$)", value=st.session_state.ex_rec)
    cus_medio_txt = col6.text_input("Custo Médio mensal (R$)", value=st.session_state.ex_cus)
    meses_txt = col7.text_input("Período (meses)", value=st.session_state.ex_meses)
    
    rec_media = parse_brl(rec_media_txt)
    cus_medio = parse_brl(cus_medio_txt)
    try: periodo_meses = int(meses_txt)
    except: periodo_meses = 0
else:
    df_padrao = pd.DataFrame([{"Mês": i+1, "Receita (R$)": 0.0, "Custo (R$)": 0.0} for i in range(12)])
    df_editado = st.data_editor(df_padrao, num_rows="dynamic", use_container_width=True)
    for index, row in df_editado.iterrows():
        dados_mensais.append({"receita": float(row["Receita (R$)"]), "custo": float(row["Custo (R$)"])})
    periodo_meses = len(dados_mensais)

st.markdown("---")
calcular = st.button("Calcular Viabilidade", use_container_width=True, type="primary")

if calcular:
    investimento_float = parse_brl(inv)
    
    if investimento_float <= 0:
        st.error("O investimento inicial deve ser maior que zero.")
    elif periodo_meses <= 0:
        st.error("O período de análise deve ter pelo menos 1 mês.")
    else:
        data = {
            "nome": nome, "tipo": tipo, "tma_anual": parse_brl(tma) / 100.0,
            "pro_labore": parse_brl(pro_labore), "investimento": investimento_float,
            "mode": "average" if "Média" in modo else "monthly",
            "receita_media": rec_media, "custo_medio": cus_medio,
            "periodo_meses": periodo_meses, "dados_mensais": dados_mensais
        }
        
        with st.spinner("Processando cálculos..."):
            analyzer = ProjectAnalyzer(data)
            res = analyzer.analyze()
            
            st.markdown("---")
            st.header("Resultado da Análise")
            
            if res['veredito'] == "APROVADO":
                st.markdown(f"<p class='aprovado'>{res['veredito']}</p>", unsafe_allow_html=True)
                st.success("Negócio economicamente viável.")
            elif res['veredito'] == "REPROVADO":
                st.markdown(f"<p class='reprovado'>{res['veredito']}</p>", unsafe_allow_html=True)
                st.error("Projeto inviável nas condições informadas.")
            else:
                st.markdown(f"<p class='revisao'>{res['veredito']}</p>", unsafe_allow_html=True)
                st.warning("Projeto no limite de viabilidade. Requer revisão.")

            st.subheader("Indicadores Principais")
            c1, c2, c3 = st.columns(3)
            c1.metric("VPL", format_brl(res['base']['vpl']))
            c2.metric("TIR Mensal", format_pct(res['base']['tir_m']))
            pb = f"{res['base']['payback']:.1f} meses" if res['base']['payback'] else "Não se paga"
            c3.metric("Payback Descontado", pb)

            c4, c5 = st.columns(2)
            limite = format_pct(res['limite_viabilidade']) if res['limite_viabilidade'] else "Inviável"
            angulo_txt = f"{res['risco_angulo']:.1f}°" if res['risco_angulo'] else "N/A"
            
            c4.write(f"**Risco ({res['risco_classificacao']})**: Ângulo de sensibilidade de {angulo_txt}. Queda limite nas vendas: {limite}.")
            
            if res['pl_cenario']:
                if res['pl_recomendado']:
                    c5.write("**Pró-Labore:** Compatível com a saúde financeira do negócio.")
                else:
                    c5.write("**Pró-Labore:** Incompatível (compromete a viabilidade).")
            else:
                c5.write("**Pró-Labore:** Não calculado.")

            st.markdown("---")
            pdf_buffer = generate_pdf_buffer(res)
            st.download_button(
                label="Baixar Relatório em PDF",
                data=pdf_buffer,
                file_name=f"Relatorio_{nome.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
