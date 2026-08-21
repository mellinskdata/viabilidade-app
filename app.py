import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utils import parse_brl, format_brl, format_pct
from core import ProjectAnalyzer
from reports import generate_pdf_buffer

# Configuração da Página
st.set_page_config(page_title="Viabilidade Econômica", page_icon="📈", layout="centered")

# Cores e Estilo
st.markdown("""
    <style>
    .big-font {font-size:20px !important;}
    .aprovado {color: #2ecc71; font-weight: bold; font-size: 28px;}
    .reprovado {color: #e74c3c; font-weight: bold; font-size: 28px;}
    .revisao {color: #f1c40f; font-weight: bold; font-size: 28px;}
    </style>
""", unsafe_allow_html=True)

# Inicializar Variáveis de Exemplo
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

# Menu Lateral (Ajuda)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.title("Ajuda e Conceitos")
    st.button("Carregar Dados de Exemplo", on_click=carregar_exemplo, use_container_width=True)
    
    with st.expander("O que significam as siglas?"):
        st.write("**VPL:** Mostra se o negócio vai gerar lucro real acima da inflação/taxa exigida.")
        st.write("**TIR:** É a rentabilidade do seu negócio.")
        st.write("**TMA:** É o mínimo que você aceita ganhar (ex: poupança).")
        st.write("**Payback:** Em quantos meses o dinheiro investido volta para o seu bolso.")
        st.write("**Pró-Labore:** Seu salário como dono.")

# Corpo do Site
st.title("📊 Análise de Viabilidade Econômica")
st.write("Descubra se o seu negócio vai dar lucro ou prejuízo de forma simples.")

# Passo 1
st.header("1. Dados Básicos")
col1, col2 = st.columns(2)
nome = col1.text_input("Nome do Negócio", value=st.session_state.ex_nome)
tipo = col2.radio("Situação", ["Negócio Futuro", "Negócio Existente (Já funciona)"])

col3, col4 = st.columns(2)
tma = col3.text_input("Taxa Mínima Aceitável ao ano (Ex: 15,00 para 15%)", value=st.session_state.ex_tma)
pro_labore = col4.text_input("Pró-Labore Desejado por mês (R$)", value=st.session_state.ex_pro)

# Passo 2
st.header("2. Receitas e Custos")
modo = st.radio("Como prefere preencher?", ["Usar Média Mensal (Mais Fácil)", "Preencher Mês a Mês (Detalhado)"])
inv = st.text_input("Qual o Investimento Inicial? (R$)", value=st.session_state.ex_inv)

dados_mensais = []
periodo_meses = 0
rec_media = 0
cus_medio = 0

if "Média" in modo:
    col5, col6, col7 = st.columns(3)
    rec_media_txt = col5.text_input("Receita Média por mês (R$)", value=st.session_state.ex_rec)
    cus_medio_txt = col6.text_input("Custo Médio por mês (R$)", value=st.session_state.ex_cus)
    meses_txt = col7.text_input("Analisar por quantos meses?", value=st.session_state.ex_meses)
    
    rec_media = parse_brl(rec_media_txt)
    cus_medio = parse_brl(cus_medio_txt)
    try: periodo_meses = int(meses_txt)
    except: periodo_meses = 0

else:
    st.info("Altere os valores diretamente na tabela abaixo:")
    df_padrao = pd.DataFrame([{"Mês": i+1, "Receita (R$)": 0.0, "Custo (R$)": 0.0} for i in range(12)])
    df_editado = st.data_editor(df_padrao, num_rows="dynamic", use_container_width=True)
    for index, row in df_editado.iterrows():
        dados_mensais.append({"receita": float(row["Receita (R$)"]), "custo": float(row["Custo (R$)"])})
    periodo_meses = len(dados_mensais)

# Passo 3: Botão Gigante
st.markdown("---")
calcular = st.button("🚀 CLIQUE AQUI PARA CALCULAR VIABILIDADE", use_container_width=True, type="primary")

if calcular:
    investimento_float = parse_brl(inv)
    
    if investimento_float <= 0:
        st.error("Por favor, preencha o Investimento Inicial com um valor maior que zero.")
    elif periodo_meses <= 0:
        st.error("O período de análise deve ter pelo menos 1 mês.")
    else:
        # Montar Dicionário pro Cérebro Financeiro
        data = {
            "nome": nome, "tipo": tipo, "tma_anual": parse_brl(tma) / 100.0,
            "pro_labore": parse_brl(pro_labore), "investimento": investimento_float,
            "mode": "average" if "Média" in modo else "monthly",
            "receita_media": rec_media, "custo_medio": cus_medio,
            "periodo_meses": periodo_meses, "dados_mensais": dados_mensais
        }
        
        with st.spinner("Analisando finanças..."):
            analyzer = ProjectAnalyzer(data)
            res = analyzer.analyze()
            
            # --- EXIBIÇÃO DOS RESULTADOS ---
            st.markdown("---")
            st.header("📋 Resultado da Análise")
            
            # Veredito Visual
            if res['veredito'] == "APROVADO":
                st.markdown(f"<p class='aprovado'>✅ {res['veredito']}</p>", unsafe_allow_html=True)
                st.success("Parabéns! Financeiramente, este é um bom negócio para se investir.")
            elif res['veredito'] == "REPROVADO":
                st.markdown(f"<p class='reprovado'>❌ {res['veredito']}</p>", unsafe_allow_html=True)
                st.error("Cuidado! Este projeto vai dar prejuízo ou não atinge o mínimo que você exigiu.")
            else:
                st.markdown(f"<p class='revisao'>⚠️ {res['veredito']}</p>", unsafe_allow_html=True)
                st.warning("O negócio até se paga, mas apresenta riscos ou rentabilidade no limite. Estude com cautela.")

            # Indicadores Principais em formato de Cards
            st.subheader("Indicadores Principais")
            c1, c2, c3 = st.columns(3)
            c1.metric("VPL (Lucro Real)", format_brl(res['base']['vpl']))
            c2.metric("Rentabilidade (TIR/mês)", format_pct(res['base']['tir_m']))
            
            pb = f"{res['base']['payback']:.1f} meses" if res['base']['payback'] else "Não se paga"
            c3.metric("Tempo de Retorno (Payback)", pb)

            # Risco e Pró Labore
            c4, c5 = st.columns(2)
            limite = format_pct(res['limite_viabilidade']) if res['limite_viabilidade'] else "Já nasce inviável"
            c4.info(f"**📉 Risco {res['risco_classificacao']}**: O negócio quebra se as vendas caírem {limite}.")
            
            if res['pl_cenario']:
                if res['pl_recomendado']:
                    c5.success("👔 **Pró-Labore:** O negócio consegue pagar o salário desejado tranquilamente.")
                else:
                    c5.error("👔 **Pró-Labore:** ATENÇÃO! Tirar esse salário vai quebrar a empresa.")
            else:
                c5.info("👔 **Pró-Labore:** Não foi solicitado cálculo de salário para o dono.")
            
            # Gráfico Simples
            st.subheader("O que acontece se as vendas caírem?")
            x_vals = [(s['variacao'] * 100) for s in res['sensibilidade']]
            y_vals = [(s['tir_m'] * 100 if s['tir_m'] else 0) for s in res['sensibilidade']]
            
            fig, ax = plt.subplots(figsize=(7, 3))
            ax.plot(x_vals, y_vals, marker='o', color='#2980b9')
            tma_p = res['base']['tma_m'] * 100
            ax.axhline(y=tma_p, color='r', linestyle='--', label="O mínimo que você aceita")
            ax.set_title("Efeito das vendas na Rentabilidade")
            ax.set_xlabel("Se as vendas mudarem em (%)")
            ax.set_ylabel("Rentabilidade ao mês (%)")
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

            # Botão de Download PDF
            st.markdown("---")
            pdf_buffer = generate_pdf_buffer(res)
            st.download_button(
                label="📄 BAIXAR RELATÓRIO COMPLETO EM PDF",
                data=pdf_buffer,
                file_name=f"Relatorio_{nome.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )