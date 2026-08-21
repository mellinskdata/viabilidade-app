import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
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
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.title("Ajuda e Conceitos")
    st.button("Carregar Dados de Exemplo", on_click=carregar_exemplo, use_container_width=True)
    
    with st.expander("O que significam as siglas?"):
        st.write("**VPL:** Mostra se o negócio vai gerar lucro real acima da TMA.")
        st.write("**TIR:** É a rentabilidade mensal do seu negócio.")
        st.write("**Payback:** Em quantos meses o dinheiro investido volta para você.")

st.title("📊 Análise de Viabilidade Econômica")
st.write("Ferramenta segura para apoio à decisão em pequenos negócios.")

st.header("1. Dados Básicos")
col1, col2 = st.columns(2)
nome = col1.text_input("Nome do Negócio", value=st.session_state.ex_nome)
tipo = col2.radio("Situação", ["Negócio Futuro", "Negócio Existente"])

col3, col4 = st.columns(2)
tma = col3.text_input("Taxa Mínima Aceitável ao ano (Ex: 15,00 para 15%)", value=st.session_state.ex_tma)
pro_labore = col4.text_input("Pró-Labore Desejado por mês (R$)", value=st.session_state.ex_pro)

st.header("2. Receitas e Custos")
modo = st.radio("Forma de preenchimento", ["Usar Média Mensal", "Preencher Mês a Mês"])
inv = st.text_input("Investimento Inicial (R$)", value=st.session_state.ex_inv)

dados_mensais = []
periodo_meses = 0
rec_media = 0
cus_medio = 0

if "Média" in modo:
    col5, col6, col7 = st.columns(3)
    rec_media_txt = col5.text_input("Receita Média por mês (R$)", value=st.session_state.ex_rec)
    cus_medio_txt = col6.text_input("Custo Médio por mês (R$)", value=st.session_state.ex_cus)
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
calcular = st.button("🚀 CALCULAR VIABILIDADE", use_container_width=True, type="primary")

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
            st.header("📋 Resultado da Análise")
            
            if res['veredito'] == "APROVADO":
                st.markdown(f"<p class='aprovado'>✅ {res['veredito']}</p>", unsafe_allow_html=True)
                st.success("Negócio altamente atrativo e economicamente viável.")
            elif res['veredito'] == "REPROVADO":
                st.markdown(f"<p class='reprovado'>❌ {res['veredito']}</p>", unsafe_allow_html=True)
                st.error("Projeto inviável nas condições informadas.")
            else:
                st.markdown(f"<p class='revisao'>⚠️ {res['veredito']}</p>", unsafe_allow_html=True)
                st.warning("Projeto no limite de viabilidade. Requer atenção.")

            st.subheader("Indicadores Principais")
            c1, c2, c3 = st.columns(3)
            c1.metric("VPL (Lucro Real)", format_brl(res['base']['vpl']))
            c2.metric("Rentabilidade (TIR/mês)", format_pct(res['base']['tir_m']))
            pb = f"{res['base']['payback']:.1f} meses" if res['base']['payback'] else "Não se paga"
            c3.metric("Payback Descontado", pb)

            c4, c5 = st.columns(2)
            limite = format_pct(res['limite_viabilidade']) if res['limite_viabilidade'] else "Inviável"
            
            # Mensagem de risco coerente com a margem real
            if res['risco_classificacao'] == "BAIXO":
                c4.success(f"🛡️ **Risco BAIXO**: O negócio é seguro e suporta uma queda de até {limite} nas vendas.")
            elif res['risco_classificacao'] == "MÉDIO":
                c4.warning(f"⚠️ **Risco MÉDIO**: O negócio suporta uma queda de até {limite} nas vendas.")
            else:
                c4.error(f"🚨 **Risco ALTO**: Qualquer oscilação pequena ({limite}) coloca o projeto em risco.")
            
            if res['pl_cenario']:
                if res['pl_recomendado']:
                    c5.success("👔 **Pró-Labore:** Compatível com a saúde financeira.")
                else:
                    c5.error("👔 **Pró-Labore:** Incompatível (compromete o lucro).")
            else:
                c5.info("👔 **Pró-Labore:** Não calculado.")
            
            # Gráfico limpo
            st.subheader("Sensibilidade das Vendas")
            x_vals = [(s['variacao'] * 100) for s in res['sensibilidade']]
            y_vals = [(s['tir_m'] * 100 if s['tir_m'] is not None else np.nan) for s in res['sensibilidade']]
            
            fig, ax = plt.subplots(figsize=(7, 3))
            tma_p = res['base']['tma_m'] * 100
            ax.plot(x_vals, y_vals, marker='o', color='#2980b9', linewidth=2)
            ax.axhline(y=tma_p, color='red', linestyle='--', label=f"TMA Mínima ({tma_p:.2f}%)")
            ax.set_title("Rentabilidade (%) x Variação nas Vendas (%)")
            ax.set_xlabel("Variação nas Vendas")
            ax.set_ylabel("TIR Mensal")
            ax.legend()
            ax.grid(True, linestyle=':', alpha=0.6)
            st.pyplot(fig)

            st.markdown("---")
            pdf_buffer = generate_pdf_buffer(res)
            st.download_button(
                label="📄 BAIXAR RELATÓRIO COMPLETO EM PDF",
                data=pdf_buffer,
                file_name=f"Relatorio_{nome.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
