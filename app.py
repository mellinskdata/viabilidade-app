"""Interface Streamlit para análise de viabilidade econômica por mês."""
import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from ajuda import TEXTOS_AJUDA, figura_faixas_risco
from core import ProjectAnalyzer
from reports import generate_pdf_buffer
from utils import parse_brl, format_brl, format_pct

st.set_page_config(page_title="Viabilidade Econômica", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  section[data-testid="stSidebar"], [data-testid="collapsedControl"] {display: none;}
  .aprovado {color: #16a34a; font-weight: 750; font-size: 1.7rem;}
  .reprovado {color: #dc2626; font-weight: 750; font-size: 1.7rem;}
  .revisao {color: #c18100; font-weight: 750; font-size: 1.7rem;}
</style>
""", unsafe_allow_html=True)


def abrir_ajuda(chave):
    st.markdown(TEXTOS_AJUDA[chave])
    if chave == "RISCO":
        fig = figura_faixas_risco()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.markdown("""
- **Até 30° — Baixo risco:** negócio mais estável.
- **Acima de 30° até 45° — Médio risco baixo:** requer atenção moderada.
- **Acima de 45° até 60° — Médio risco alto:** muito sensível à variação das vendas.
- **Acima de 60° — Alto risco:** pequenos imprevistos podem comprometer a rentabilidade.

*O ângulo é um indicador simplificado de sensibilidade; não representa probabilidade de perda.*
""")


def rotulo_com_ajuda(rotulo, chave):
    # Ajuda clicável ao lado da palavra-chave, sem barra lateral.
    nome, botao, _ = st.columns([3.8, 0.65, 2.6], gap="small", vertical_alignment="center")
    nome.markdown(f"**{rotulo}**")
    with botao.popover("?", help=f"O que significa {rotulo}?"):
        abrir_ajuda(chave)


def carregar_exemplo():
    st.session_state["nome"] = "Projeto Padrão (Exemplo)"
    st.session_state["tma"] = "15,00"
    st.session_state["investimento"] = "29.400,00"
    st.session_state["meses"] = 12
    st.session_state["historico_mensal"] = [{"receita": 10000.0, "custo": 4000.0} for _ in range(12)]
    st.session_state.pop("resultado", None)
    st.session_state.pop("dados_calculados", None)
    # Evita reutilizar os ajustes da tabela anterior ao carregar novo exemplo.
    for k in list(st.session_state):
        if str(k).startswith("editor_mensal_"):
            del st.session_state[k]


if "nome" not in st.session_state:
    st.session_state["nome"] = ""
if "tma" not in st.session_state:
    st.session_state["tma"] = ""
if "investimento" not in st.session_state:
    st.session_state["investimento"] = ""
if "meses" not in st.session_state:
    st.session_state["meses"] = 12
if "historico_mensal" not in st.session_state:
    st.session_state["historico_mensal"] = []

st.title("Análise de Viabilidade Econômica")
st.write("Descubra se o seu negócio possui viabilidade financeira.")
st.button("Carregar dados de exemplo", on_click=carregar_exemplo)

st.header("1. Dados Básicos")
st.text_input("Nome do Negócio", key="nome")
rotulo_com_ajuda("TMA (anual, %)", "TMA")
st.text_input("Taxa Mínima de Atratividade ao ano (Ex.: 15,00)", key="tma", label_visibility="collapsed", placeholder="Ex.: 15,00")

st.header("2. Receitas e Custos")
st.text_input("Investimento Inicial (R$)", key="investimento")
st.number_input("Quantos meses deseja analisar?", min_value=1, max_value=240, step=1, key="meses")
rotulo_com_ajuda("Custos mensais", "CUSTOS")
st.caption("Preencha as receitas e os custos de cada mês diretamente na tabela. O mês não pode ser editado.")

meses = int(st.session_state["meses"])
historico = st.session_state["historico_mensal"]
while len(historico) < meses:
    historico.append({"receita": 0.0, "custo": 0.0})

tabela = pd.DataFrame([
    {"Mês": i + 1, "Receita (R$)": historico[i]["receita"], "Custo (R$)": historico[i]["custo"]}
    for i in range(meses)
])
editada = st.data_editor(
    tabela,
    key=f"editor_mensal_{meses}",
    num_rows="fixed",
    hide_index=True,
    disabled=["Mês"],
    use_container_width=True,
    column_config={
        "Mês": st.column_config.NumberColumn("Mês", format="%d", width="small"),
        "Receita (R$)": st.column_config.NumberColumn("Receita (R$)", format="R$ %.2f", min_value=0.0, step=100.0, required=True),
        "Custo (R$)": st.column_config.NumberColumn("Custo (R$)", format="R$ %.2f", min_value=0.0, step=100.0, required=True),
    },
)
dados_mensais = []
for i, linha in editada.iterrows():
    receita = float(linha["Receita (R$)"])
    custo = float(linha["Custo (R$)"])
    historico[i] = {"receita": receita, "custo": custo}
    dados_mensais.append({"receita": receita, "custo": custo})

st.divider()
calcular = st.button("CALCULAR VIABILIDADE", use_container_width=True, type="primary")

dados = {
    "nome": st.session_state["nome"].strip() or "Projeto",
    "investimento": parse_brl(st.session_state["investimento"]),
    "tma_anual": parse_brl(st.session_state["tma"]) / 100.0,
    "dados_mensais": dados_mensais,
}

if calcular:
    if dados["investimento"] <= 0 or not math.isfinite(dados["investimento"]):
        st.error("Informe um investimento inicial maior que zero.")
    elif not 0 <= dados["tma_anual"] <= 10:
        st.error("Informe uma TMA válida, entre 0% e 1.000% ao ano.")
    elif any(not math.isfinite(m["receita"]) or not math.isfinite(m["custo"]) or m["receita"] < 0 or m["custo"] < 0 for m in dados_mensais):
        st.error("Receitas e custos devem ser números válidos e não negativos.")
    else:
        with st.spinner("Analisando finanças..."):
            st.session_state["resultado"] = ProjectAnalyzer(dados).analyze()
            st.session_state["dados_calculados"] = dados.copy()

# Mantém os resultados ao abrir ajudas; evita mostrar um cálculo antigo após edições.
if "resultado" in st.session_state and st.session_state.get("dados_calculados") != dados:
    del st.session_state["resultado"]

if "resultado" in st.session_state:
    res = st.session_state["resultado"]
    st.divider()
    st.header("Resultado da Análise")
    if res["veredito"] == "APROVADO":
        st.markdown("<p class='aprovado'>APROVADO</p>", unsafe_allow_html=True)
        st.success("Financeiramente, este é um bom negócio para se investir, segundo os critérios do aplicativo.")
    elif res["veredito"] == "REPROVADO":
        st.markdown("<p class='reprovado'>REPROVADO</p>", unsafe_allow_html=True)
        st.error("O projeto não atinge os critérios mínimos de retorno. Revise as estimativas.")
    else:
        st.markdown("<p class='revisao'>REVISÃO RECOMENDADA</p>", unsafe_allow_html=True)
        st.warning("O negócio apresenta riscos ou rentabilidade limitada. Analise com cautela.")

    st.subheader("Indicadores Financeiros")
    c1, c2, c3 = st.columns(3)
    with c1:
        rotulo_com_ajuda("VPL", "VPL")
        st.metric("Valor presente líquido", format_brl(res["base"]["vpl"]))
    with c2:
        rotulo_com_ajuda("TIR", "TIR")
        st.metric("TIR anual", format_pct(res["base"]["tir_a"]))
    with c3:
        rotulo_com_ajuda("TIRM", "TIRM")
        st.metric("TIRM anual", format_pct(res["base"]["tirm_a"]))

    rotulo_com_ajuda("Payback Descontado", "PAYBACK")
    pb = res["base"]["payback_descontado"]
    st.metric("Retorno do investimento (descontado)", f"{pb:.1f} meses" if pb is not None else "Não recupera no período")

    st.subheader("Análise de Risco — Sensibilidade da TIR")
    rotulo_com_ajuda("Classificação de risco", "RISCO")
    grau = res["risco_angulo"]
    if grau is None:
        st.info("Risco indefinido para os dados informados.")
    else:
        st.info(f"Classificação: **{res['risco_classificacao']}** (ângulo: {grau:.1f}°).")
    if res["limite_viabilidade"] is not None and res["base"]["vpl"] > 0:
        st.caption(f"Queda máxima estimada das receitas até o VPL atingir zero: {format_pct(res['limite_viabilidade'])}.")

    st.divider()
    pdf_buffer = generate_pdf_buffer(res)
    st.download_button(
        label="BAIXAR RELATÓRIO COMPLETO EM PDF",
        data=pdf_buffer,
        file_name=f"Relatorio_{''.join(c if c.isalnum() or c in '-_' else '_' for c in dados['nome'])}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )