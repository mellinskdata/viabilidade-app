import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utils import parse_brl, format_brl, format_pct
from core import ProjectAnalyzer
from reports import generate_pdf_buffer

# Configuracao da Pagina
st.set_page_config(page_title="Viabilidade Economica", layout="centered")

# Cores e Estilo
st.markdown("""
    <style>
    .big-font {font-size:20px !important;}
    .aprovado {color: #2ecc71; font-weight: bold; font-size: 28px;}
    .reprovado {color: #e74c3c; font-weight: bold; font-size: 28px;}
    .revisao {color: #f1c40f; font-weight: bold; font-size: 28px;}
    </style>
""", unsafe_allow_html=True)

# Inicializar Variaveis de Exemplo
if "ex_nome" not in st.session_state:
    st.session_state.update({
        "ex_nome": "", "ex_tma": "", "ex_pro": "", "ex_inv": "", 
        "ex_rec": "", "ex_cus": "", "ex_meses": "12"
    })

def carregar_exemplo():
    st.session_state.update({
        "ex_nome": "Projeto Padrao (Exemplo)", "ex_tma": "15,00", "ex_pro": "2.000,00", 
        "ex_inv": "29.400,00", "ex_rec": "10.000,00", "ex_cus": "4.000,00", "ex_meses": "12"
    })

# Menu Lateral (Ajuda)
with st.sidebar:
    st.title("Ajuda e Conceitos")
    st.button("Carregar Dados de Exemplo", on_click=carregar_exemplo, use_container_width=True)
    
    with st.expander("O que significam as siglas?"):
        st.write("**VPL:** Mostra se o negocio vai gerar lucro real acima da inflacao/taxa exigida.")
        st.write("**TIR:** E a rentabilidade do seu negocio.")
        st.write("**TIRM:** Taxa Interna de Retorno Modificada (considera taxa de reinvestimento).")
        st.write("**TMA:** E o minimo que voce aceita ganhar.")
        st.write("**Payback:** Em quantos meses o dinheiro investido retorna.")
        st.write("**Pro-Labore:** Seu salario como dono.")

# Corpo do Site
st.title("Analise de Viabilidade Economica")
st.write("Descubra se o seu negocio possui viabilidade financeira.")

# Passo 1
st.header("1. Dados Basicos")
col1, col2 = st.columns(2)
nome = col1.text_input("Nome do Negocio", value=st.session_state.ex_nome)
tipo = col2.radio("Situacao", ["Negocio Futuro", "Negocio Existente (Ja funciona)"])

col3, col4 = st.columns(2)
tma = col3.text_input("Taxa Minima Aceitavel ao ano (Ex: 15,00 para 15%)", value=st.session_state.ex_tma)
pro_labore = col4.text_input("Pro-Labore Desejado por mes (R$)", value=st.session_state.ex_pro)

# Passo 2
st.header("2. Receitas e Custos")
modo = st.radio("Como prefere preencher?", ["Usar Media Mensal (Mais Facil)", "Preencher Mes a Mes (Detalhado)"])
inv = st.text_input("Qual o Investimento Inicial? (R$)", value=st.session_state.ex_inv)

dados_mensais = []
periodo_meses = 0
rec_media = 0
cus_medio = 0

if "Media" in modo:
    col5, col6, col7 = st.columns(3)
    rec_media_txt = col5.text_input("Receita Media por mes (R$)", value=st.session_state.ex_rec)
    cus_medio_txt = col6.text_input("Custo Medio por mes (R$)", value=st.session_state.ex_cus)
    meses_txt = col7.text_input("Analisar por quantos meses?", value=st.session_state.ex_meses)
    
    rec_media = parse_brl(rec_media_txt)
    cus_medio = parse_brl(cus_medio_txt)
    try: periodo_meses = int(meses_txt)
    except: periodo_meses = 0

else:
    st.info("Altere os valores diretamente na tabela abaixo:")
    df_padrao = pd.DataFrame([{"Mes": i+1, "Receita (R$)": 0.0, "Custo (R$)": 0.0} for i in range(12)])
    df_editado = st.data_editor(df_padrao, num_rows="dynamic", use_container_width=True)
    for index, row in df_editado.iterrows():
        dados_mensais.append({"receita": float(row["Receita (R$)"]), "custo": float(row["Custo (R$)"])})
    periodo_meses = len(dados_mensais)

# Passo 3: Botao Principal
st.markdown("---")
calcular = st.button("CLIQUE AQUI PARA CALCULAR VIABILIDADE", use_container_width=True, type="primary")

if calcular:
    investimento_float = parse_brl(inv)
    
    if investimento_float <= 0:
        st.error("Por favor, preencha o Investimento Inicial com um valor maior que zero.")
    elif periodo_meses <= 0:
        st.error("O periodo de analise deve ter pelo menos 1 mes.")
    else:
        data = {
            "nome": nome, "tipo": tipo, "tma_anual": parse_brl(tma) / 100.0,
            "pro_labore": parse_brl(pro_labore), "investimento": investimento_float,
            "mode": "average" if "Media" in modo else "monthly",
            "receita_media": rec_media, "custo_medio": cus_medio,
            "periodo_meses": periodo_meses, "dados_mensais": dados_mensais
        }
        
        with st.spinner("Analisando financas..."):
            analyzer = ProjectAnalyzer(data)
            res = analyzer.analyze()
            
            # --- EXIBICAO DOS RESULTADOS ---
            st.markdown("---")
            st.header("Resultado da Analise")
            
            # Veredito Visual
            if res['veredito'] == "APROVADO":
                st.markdown(f"<p class='aprovado'>APROVADO</p>", unsafe_allow_html=True)
                st.success("Financeiramente, este e um bom negocio para se investir.")
            elif res['veredito'] == "REPROVADO":
                st.markdown(f"<p class='reprovado'>REPROVADO</p>", unsafe_allow_html=True)
                st.error("Cuidado! Este projeto vai dar prejuizo ou nao atinge a rentabilidade minima exigida.")
            else:
                st.markdown(f"<p class='revisao'>REVISAO RECOMENDADA</p>", unsafe_allow_html=True)
                st.warning("O negocio se paga, mas apresenta riscos e rentabilidade limitados. Estude com cautela.")

            # Indicadores Principais - Bloco de Metricas
            st.subheader("Indicadores Financeiros")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("VPL (Lucro Real)", format_brl(res['base']['vpl']))
            c2.metric("TIR Mensal", format_pct(res['base']['tir_m']))
            c3.metric("TIR Anual", format_pct(res['base']['tir_a']))
            
            c4, c5, c6 = st.columns(3)
            c4.metric("TIRM Mensal", format_pct(res['base']['tirm_m']))
            
            pb_simples = f"{res['base']['payback_simples']:.1f} meses" if res['base']['payback_simples'] else "Nao recupera"
            pb_desc = f"{res['base']['payback_descontado']:.1f} meses" if res['base']['payback_descontado'] else "Nao recupera"
            
            c5.metric("Payback Simples", pb_simples)
            c6.metric("Payback Descontado", pb_desc)

            # Risco e Pro Labore
            st.subheader("Analise de Risco e Pro-Labore")
            limite = format_pct(res['limite_viabilidade']) if res['limite_viabilidade'] else "Inviavel"
            angulo_str = f"{res['risco_angulo']:.1f} graus" if res['risco_angulo'] is not None else "Indefinido"
            
            st.info(f"Classificacao de Risco: {res['risco_classificacao']} (Angulo: {angulo_str}). O negocio entra no prejuizo se as receitas cairem {limite}.")
            
            if res['pl_cenario']:
                if res['pl_recomendado']:
                    st.success("Pro-Labore: O negocio consegue pagar o salario desejado sem quebrar o caixa.")
                else:
                    st.error("Pro-Labore: ATENCAO! O projeto se torna inviavel ao retirar esse salario mensal.")
            else:
                st.info("Pro-Labore: Nao foi solicitado calculo de remuneracao para os socios.")
            
            # Grafico de Sensibilidade
            st.subheader("Sensibilidade e Ponto de Equilibrio")
            x_vals = [(s['variacao'] * 100) for s in res['sensibilidade']]
            y_vals = [(s['tir_m'] * 100 if s['tir_m'] else 0) for s in res['sensibilidade']]
            
            fig, ax = plt.subplots(figsize=(7, 3))
            ax.plot(x_vals, y_vals, marker='o', color='#2980b9')
            tma_p = res['base']['tma_m'] * 100
            ax.axhline(y=tma_p, color='r', linestyle='--', label=f"TMA ({tma_p:.2f}% ao mes)")
            ax.set_title("Efeito da variacao das Vendas na TIR Mensal")
            ax.set_xlabel("Variacao nas Vendas (%)")
            ax.set_ylabel("Rentabilidade ao mes (%)")
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

            # Botao de Download PDF
            st.markdown("---")
            pdf_buffer = generate_pdf_buffer(res)
            st.download_button(
                label="BAIXAR RELATORIO COMPLETO EM PDF",
                data=pdf_buffer,
                file_name=f"Relatorio_{nome.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
