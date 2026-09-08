"""
app.py
-------
Interface Streamlit do motor de engenharia economica.

Coleta as premissas do projeto (nome, tipo presente/futuro, periodo,
investimento, receita/custo medios ou lancamentos mensais customizados,
pro-labore e TMA), aciona o motor de calculo em core.py e apresenta os
indicadores essenciais (TIR, TIRM, Payback, risco e veredito), alem de
permitir a exportacao do relatorio executivo em PDF via reports.py.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import core
import reports
from utils import (
    formatar_meses,
    formatar_percentual,
    rotulo_risco_para_cor,
    validar_entradas_basicas,
)


st.set_page_config(
    page_title="Motor de Engenharia Economica",
    layout="wide",
)

st.title("Motor de Engenharia Economica")
st.caption("Analise de viabilidade financeira de projetos: TIR, TIRM, Payback e Risco.")

if "resultado" not in st.session_state:
    st.session_state["resultado"] = None


# ---------------------------------------------------------------------------
# Formulario de entrada
# ---------------------------------------------------------------------------

with st.form("formulario_projeto"):
    st.subheader("Dados do Projeto")

    col_nome, col_tipo, col_tma = st.columns(3)
    with col_nome:
        nome_projeto = st.text_input("Nome do projeto", value="Meu Projeto")
    with col_tipo:
        tipo_projeto = st.selectbox("Projeto presente ou futuro", ["Futuro", "Presente"])
    with col_tma:
        tma_anual_pct = st.number_input(
            "TMA anual (%)",
            min_value=0.0,
            max_value=500.0,
            value=15.0,
            step=0.5,
            help="Taxa Minima de Atratividade anual, usada para descontar o fluxo de caixa.",
        )

    if tipo_projeto == "Futuro":
        st.caption(
            "Projeto futuro: o investimento inicial ocorre no mes 0, antes do "
            "inicio das operacoes."
        )
    else:
        st.caption(
            "Projeto presente: o investimento inicial representa aporte ou "
            "expansao a partir de agora, para um negocio ja em operacao."
        )

    col_periodo, col_investimento, col_prolabore = st.columns(3)
    with col_periodo:
        periodo_meses = st.number_input(
            "Periodo de analise (meses)", min_value=1, max_value=600, value=36, step=1
        )
    with col_investimento:
        investimento_inicial = st.number_input(
            "Investimento inicial (R$)", min_value=0.0, value=50000.0, step=1000.0
        )
    with col_prolabore:
        pro_labore = st.number_input(
            "Pro-labore desejado / mes (R$)",
            min_value=0.0,
            value=3000.0,
            step=100.0,
            help="Retirada mensal desejada pelo empreendedor, tratada como custo do projeto.",
        )

    st.markdown("---")
    st.subheader("Fluxo de Caixa")

    modo_selecionado = st.radio(
        "Como deseja informar o fluxo de caixa?",
        ["Media mensal (receita e custo fixos)", "Lancamentos mensais customizados"],
        horizontal=True,
    )
    modo_fluxo = "media" if modo_selecionado.startswith("Media") else "customizado"

    receita_media = 0.0
    custo_medio = 0.0
    lancamentos_mensais = None

    if modo_fluxo == "media":
        col_receita, col_custo = st.columns(2)
        with col_receita:
            receita_media = st.number_input(
                "Receita media / mes (R$)", min_value=0.0, value=15000.0, step=500.0
            )
        with col_custo:
            custo_medio = st.number_input(
                "Custo medio / mes (R$)", min_value=0.0, value=8000.0, step=500.0
            )
    else:
        st.caption("Informe a receita e o custo previstos para cada mes do periodo de analise.")
        tabela_padrao = pd.DataFrame(
            {
                "mes": list(range(1, int(periodo_meses) + 1)),
                "receita": [15000.0] * int(periodo_meses),
                "custo": [8000.0] * int(periodo_meses),
            }
        )
        tabela_editada = st.data_editor(
            tabela_padrao,
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
            column_config={
                "mes": st.column_config.NumberColumn("Mes", disabled=True),
                "receita": st.column_config.NumberColumn("Receita (R$)", min_value=0.0),
                "custo": st.column_config.NumberColumn("Custo (R$)", min_value=0.0),
            },
            key="tabela_lancamentos",
        )
        lancamentos_mensais = tabela_editada.to_dict("records")

    calcular = st.form_submit_button("Calcular Viabilidade", use_container_width=True)


# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------

if calcular:
    erros = validar_entradas_basicas(
        periodo_meses=int(periodo_meses),
        investimento_inicial=investimento_inicial,
        tma_anual=tma_anual_pct / 100,
    )
    if erros:
        for erro in erros:
            st.error(erro)
    else:
        try:
            resultado = core.executar_analise(
                nome_projeto=nome_projeto or "Projeto sem nome",
                tipo_projeto=tipo_projeto,
                tma_anual=tma_anual_pct / 100,
                periodo_meses=int(periodo_meses),
                investimento_inicial=investimento_inicial,
                modo_fluxo=modo_fluxo,
                receita_media=receita_media,
                custo_medio=custo_medio,
                pro_labore=pro_labore,
                lancamentos_mensais=lancamentos_mensais,
            )
            st.session_state["resultado"] = resultado
        except core.ErroCalculoFinanceiro as erro:
            st.error(f"Erro no calculo financeiro: {erro}")
        except ValueError as erro:
            st.error(f"Entrada invalida: {erro}")


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------

resultado = st.session_state.get("resultado")

if resultado:
    st.markdown("---")
    st.subheader(f"Resultados - {resultado['nome_projeto']}")

    col_tir, col_tirm, col_payback = st.columns(3)
    with col_tir:
        st.metric("TIR anual", formatar_percentual(resultado["tir_anual"]))
        st.caption(f"TIR mensal: {formatar_percentual(resultado['tir_mensal'])}")
    with col_tirm:
        st.metric("TIRM anual", formatar_percentual(resultado["tirm_anual"]))
        st.caption(f"TIRM mensal: {formatar_percentual(resultado['tirm_mensal'])}")
    with col_payback:
        st.metric("Payback simples", formatar_meses(resultado["payback_simples_meses"]))
        st.caption(
            f"Payback descontado: {formatar_meses(resultado['payback_descontado_meses'])}"
        )

    col_risco, col_veredito = st.columns([1, 2])
    with col_risco:
        risco = resultado["risco"]
        cor = rotulo_risco_para_cor(risco)
        st.markdown("**Analise de Risco**")
        st.markdown(
            f"<div style='padding:14px;border-radius:8px;background-color:{cor};"
            f"color:white;text-align:center;font-size:1.1rem;font-weight:600;'>"
            f"Risco {risco}</div>",
            unsafe_allow_html=True,
        )
        inclinacao = resultado["sensibilidade"]["inclinacao_tir"]
        st.caption(
            f"Sensibilidade: {inclinacao:.2f} p.p. de TIR mensal por 1% de "
            "variacao na receita projetada."
        )

    with col_veredito:
        veredito = resultado["veredito"]
        st.markdown("**Veredito**")
        mensagem = f"**{veredito['titulo']}**\n\n{veredito['justificativa']}"
        if veredito["severidade"] == "positivo":
            st.success(mensagem)
        elif veredito["severidade"] == "atencao":
            st.warning(mensagem)
        else:
            st.error(mensagem)

    with st.expander("Detalhes da analise de sensibilidade"):
        sensibilidade = resultado["sensibilidade"]
        st.caption(
            "A variacao e aplicada apenas sobre a receita projetada (custo e "
            "pro-labore permanecem fixos). O risco e classificado com base na "
            "inclinacao da reta TIR mensal x variacao (coluna destacada abaixo)."
        )
        df_sensibilidade = pd.DataFrame(
            {
                "Variacao na receita (%)": sensibilidade["variacoes_percentuais"],
                "TIR mensal resultante (%)": sensibilidade["tir_mensal_resultante_pct"],
                "TIR anual resultante (%)": sensibilidade["tir_anual_resultante_pct"],
                "VPL resultante (R$)": sensibilidade["vpl_resultante"],
            }
        )
        st.dataframe(df_sensibilidade, use_container_width=True, hide_index=True)
        st.line_chart(
            df_sensibilidade.set_index("Variacao na receita (%)")["TIR mensal resultante (%)"]
        )

    st.markdown("---")
    st.subheader("Exportar Relatorio")
    buffer_pdf = reports.gerar_relatorio_pdf(resultado)
    nome_arquivo = resultado["nome_projeto"].strip().replace(" ", "_") or "projeto"
    st.download_button(
        label="Baixar relatorio em PDF",
        data=buffer_pdf,
        file_name=f"relatorio_viabilidade_{nome_arquivo}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
else:
    st.info("Preencha os dados do projeto e clique em Calcular Viabilidade para ver os resultados.")
