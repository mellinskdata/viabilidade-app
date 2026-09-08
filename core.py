"""
core.py
--------
Motor de calculo de engenharia economica.

Responsavel por:
- Construcao da serie de fluxo de caixa (investimento inicial + fluxos
  mensais liquidos de receita, custo e pro-labore).
- Calculo de indicadores financeiros: VPL, TIR (mensal/anual), TIRM
  (mensal/anual), Payback Simples e Payback Descontado.
- Analise de sensibilidade da TIR e do VPL frente a variacoes percentuais
  no fluxo de caixa/receita, com calculo da inclinacao da reta (regressao
  linear) como indicador de risco.
- Classificacao de risco (Baixo / Medio / Alto) e geracao do veredito
  final do projeto.

Este modulo nao depende do Streamlit nem do ReportLab, apenas de numpy e
numpy_financial, para poder ser usado e testado de forma isolada.
"""

from __future__ import annotations

import numpy as np
import numpy_financial as npf


# ---------------------------------------------------------------------------
# Constantes e parametros padrao
# ---------------------------------------------------------------------------

MESES_POR_ANO = 12

# Faixa de variacao (%) usada na analise de sensibilidade do fluxo/receita
VARIACOES_SENSIBILIDADE = [-30, -20, -10, 0, 10, 20, 30]

# Limiares (em pontos percentuais de TIR MENSAL por 1% de variacao na
# receita) usados para classificar o risco a partir da inclinacao da reta
# de sensibilidade. A inclinacao e calculada sobre a TIR mensal (e nao a
# TIR anual) porque a anualizacao ((1+i)^12 - 1) amplia de forma nao
# linear qualquer variacao de fluxo, distorcendo a comparacao de risco
# entre projetos com paybacks muito curtos. Os limiares abaixo foram
# calibrados empiricamente sobre uma ampla faixa de projetos de pequeno
# porte (payback entre 1 e 40 meses) e podem ser recalibrados conforme o
# perfil da carteira analisada.
LIMIAR_RISCO_BAIXO = 0.30
LIMIAR_RISCO_MEDIO = 0.55


class ErroCalculoFinanceiro(Exception):
    """Erro generico levantado quando um indicador nao pode ser calculado."""


# ---------------------------------------------------------------------------
# Conversao de taxas
# ---------------------------------------------------------------------------

def taxa_anual_para_mensal(taxa_anual: float) -> float:
    """Converte uma taxa anual efetiva (fracao decimal) em taxa mensal equivalente."""
    if taxa_anual <= -1:
        raise ValueError("Taxa anual invalida: deve ser maior que -100%.")
    return (1 + taxa_anual) ** (1 / MESES_POR_ANO) - 1


def taxa_mensal_para_anual(taxa_mensal: float) -> float:
    """Converte uma taxa mensal efetiva (fracao decimal) em taxa anual equivalente."""
    if taxa_mensal <= -1:
        raise ValueError("Taxa mensal invalida: deve ser maior que -100%.")
    return (1 + taxa_mensal) ** MESES_POR_ANO - 1


# ---------------------------------------------------------------------------
# Construcao do fluxo de caixa
# ---------------------------------------------------------------------------
#
# A receita e o custo mensais sao mantidos como series separadas (e nao ja
# somadas em um unico fluxo liquido) porque a analise de sensibilidade
# precisa variar especificamente a RECEITA, mantendo custo e pro-labore
# fixos. Se apenas o fluxo liquido ja consolidado fosse escalado, um
# projeto com fluxo liquido mensal negativo teria o sinal da sensibilidade
# invertido (aumentar a "variacao" pioraria o resultado em vez de melhorar).

def construir_componentes_mensais(
    periodo_meses: int,
    modo: str,
    receita_media: float = 0.0,
    custo_medio: float = 0.0,
    lancamentos_mensais: list[dict] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Retorna duas series de tamanho periodo_meses (meses 1..periodo_meses):
    receita_mensal e custo_mensal, ANTES do desconto do pro-labore e sem o
    investimento inicial.

    modo: "media" (receita/custo fixos) ou "customizado" (lancamento por mes)
    lancamentos_mensais: lista de dicts, ex.
        [{"mes": 1, "receita": 15000.0, "custo": 8000.0}, ...]
        obrigatorio quando modo == "customizado"
    """
    if periodo_meses <= 0:
        raise ValueError("O periodo de analise deve ser maior que zero.")

    if modo == "media":
        receita_mensal = np.full(periodo_meses, float(receita_media))
        custo_mensal = np.full(periodo_meses, float(custo_medio))

    elif modo == "customizado":
        if not lancamentos_mensais:
            raise ValueError(
                "Modo customizado selecionado, mas nenhum lancamento mensal foi informado."
            )
        mapa = {}
        for item in lancamentos_mensais:
            try:
                mes = int(item.get("mes"))
            except (TypeError, ValueError):
                continue
            mapa[mes] = item

        receita_mensal = np.zeros(periodo_meses)
        custo_mensal = np.zeros(periodo_meses)
        for mes in range(1, periodo_meses + 1):
            item = mapa.get(mes, {"receita": 0.0, "custo": 0.0})
            receita_mensal[mes - 1] = float(item.get("receita", 0.0) or 0.0)
            custo_mensal[mes - 1] = float(item.get("custo", 0.0) or 0.0)
    else:
        raise ValueError(f"Modo de fluxo desconhecido: {modo!r}")

    return receita_mensal, custo_mensal


def montar_fluxo_caixa(
    investimento_inicial: float,
    receita_mensal: np.ndarray,
    custo_mensal: np.ndarray,
    pro_labore: float = 0.0,
) -> np.ndarray:
    """
    Monta a serie de fluxo de caixa completa a partir das series de receita
    e custo mensais, do pro-labore e do investimento inicial.

    O array resultante tem tamanho (len(receita_mensal) + 1):
        posicao 0            -> -investimento_inicial (saida em t=0)
        posicoes 1..periodo  -> receita - custo - pro_labore, mes a mes
    """
    fluxo = np.zeros(len(receita_mensal) + 1)
    fluxo[0] = -abs(investimento_inicial)
    fluxo[1:] = receita_mensal - custo_mensal - pro_labore
    return fluxo


def construir_fluxo_caixa(
    investimento_inicial: float,
    periodo_meses: int,
    modo: str,
    receita_media: float = 0.0,
    custo_medio: float = 0.0,
    pro_labore: float = 0.0,
    lancamentos_mensais: list[dict] | None = None,
) -> np.ndarray:
    """
    Funcao de conveniencia que combina construir_componentes_mensais e
    montar_fluxo_caixa em uma unica chamada, retornando diretamente o
    fluxo de caixa liquido completo (tamanho periodo_meses + 1).
    """
    receita_mensal, custo_mensal = construir_componentes_mensais(
        periodo_meses=periodo_meses,
        modo=modo,
        receita_media=receita_media,
        custo_medio=custo_medio,
        lancamentos_mensais=lancamentos_mensais,
    )
    return montar_fluxo_caixa(investimento_inicial, receita_mensal, custo_mensal, pro_labore)


# ---------------------------------------------------------------------------
# Indicadores financeiros
# ---------------------------------------------------------------------------

def calcular_vpl(fluxo_caixa: np.ndarray, taxa_mensal: float) -> float:
    """Valor Presente Liquido do fluxo de caixa, descontado pela TMA mensal."""
    try:
        return float(npf.npv(taxa_mensal, fluxo_caixa))
    except Exception as exc:
        raise ErroCalculoFinanceiro(f"Falha ao calcular o VPL: {exc}") from exc


def calcular_tir_mensal(fluxo_caixa: np.ndarray) -> float | None:
    """
    TIR mensal (taxa periodica). Retorna None quando o calculo nao converge
    (por exemplo, fluxo sem mudanca de sinal ou nao convergencia numerica).
    """
    try:
        tir = npf.irr(fluxo_caixa)
    except Exception:
        return None
    if tir is None:
        return None
    try:
        if np.isnan(tir) or np.isinf(tir):
            return None
    except TypeError:
        return None
    return float(tir)


def calcular_tir_anual(tir_mensal: float | None) -> float | None:
    """Converte a TIR mensal em TIR anual equivalente."""
    if tir_mensal is None:
        return None
    try:
        return taxa_mensal_para_anual(tir_mensal)
    except ValueError:
        return None


def calcular_tirm_mensal(
    fluxo_caixa: np.ndarray,
    taxa_financiamento_mensal: float,
    taxa_reinvestimento_mensal: float,
) -> float | None:
    """
    TIR Modificada (MIRR) mensal, considerando a taxa de financiamento
    (aplicada aos fluxos negativos) e a taxa de reinvestimento (aplicada
    aos fluxos positivos).
    """
    try:
        tirm = npf.mirr(fluxo_caixa, taxa_financiamento_mensal, taxa_reinvestimento_mensal)
    except Exception:
        return None
    if tirm is None:
        return None
    try:
        if np.isnan(tirm) or np.isinf(tirm):
            return None
    except TypeError:
        return None
    return float(tirm)


def calcular_tirm_anual(tirm_mensal: float | None) -> float | None:
    """Converte a TIRM mensal em TIRM anual equivalente."""
    if tirm_mensal is None:
        return None
    try:
        return taxa_mensal_para_anual(tirm_mensal)
    except ValueError:
        return None


def payback_simples(fluxo_caixa: np.ndarray) -> float | None:
    """
    Payback simples, em meses (com fracao), calculado sobre o fluxo de
    caixa NAO descontado. Retorna None se o investimento nunca e
    recuperado dentro do periodo analisado.
    """
    acumulado = np.cumsum(fluxo_caixa)
    if acumulado[-1] < 0:
        return None

    indice_recuperacao = int(np.argmax(acumulado >= 0))
    if indice_recuperacao == 0:
        return 0.0

    saldo_anterior = acumulado[indice_recuperacao - 1]
    fluxo_do_mes = fluxo_caixa[indice_recuperacao]
    fracao = 0.0 if fluxo_do_mes == 0 else -saldo_anterior / fluxo_do_mes
    return float((indice_recuperacao - 1) + fracao)


def payback_descontado(fluxo_caixa: np.ndarray, taxa_mensal: float) -> float | None:
    """
    Payback descontado, em meses (com fracao), trazendo cada fluxo a valor
    presente pela TMA mensal antes de acumular. Retorna None se o
    investimento nunca e recuperado dentro do periodo analisado.
    """
    periodos = np.arange(len(fluxo_caixa))
    fluxo_descontado = fluxo_caixa / (1 + taxa_mensal) ** periodos
    acumulado = np.cumsum(fluxo_descontado)

    if acumulado[-1] < 0:
        return None

    indice_recuperacao = int(np.argmax(acumulado >= 0))
    if indice_recuperacao == 0:
        return 0.0

    saldo_anterior = acumulado[indice_recuperacao - 1]
    fluxo_do_mes = fluxo_descontado[indice_recuperacao]
    fracao = 0.0 if fluxo_do_mes == 0 else -saldo_anterior / fluxo_do_mes
    return float((indice_recuperacao - 1) + fracao)


# ---------------------------------------------------------------------------
# Analise de sensibilidade e classificacao de risco
# ---------------------------------------------------------------------------

def analise_sensibilidade(
    investimento_inicial: float,
    receita_mensal: np.ndarray,
    custo_mensal: np.ndarray,
    pro_labore: float,
    taxa_mensal: float,
    variacoes_percentuais: list[int] | None = None,
) -> dict:
    """
    Varia especificamente a RECEITA mensal (mantendo custo e pro-labore
    fixos) dentro de uma faixa percentual e recalcula a TIR (mensal e
    anual) e o VPL para cada cenario. Em seguida ajusta uma reta (regressao
    linear) entre a variacao percentual aplicada a receita e a TIR MENSAL
    resultante; a inclinacao dessa reta e usada como indicador de risco do
    projeto (ver classificar_risco).

    Duas escolhas de projeto importantes:
    - Varia-se apenas a receita (e nao o fluxo liquido ja consolidado) para
      evitar inversao de sinal em projetos cujo fluxo liquido mensal seja
      negativo, refletindo de forma mais realista o risco comercial.
    - A inclinacao de risco usa a TIR MENSAL (nao a anual), pois anualizar
      ((1+i)^12 - 1) amplia de forma nao linear qualquer variacao de
      fluxo, o que distorceria a comparacao de risco entre projetos com
      paybacks muito curtos e retornos mensais elevados. A TIR anual
      resultante de cada cenario ainda e retornada para fins de exibicao.
    """
    if variacoes_percentuais is None:
        variacoes_percentuais = VARIACOES_SENSIBILIDADE

    variacoes = []
    tir_mensal_resultados_pct = []
    tir_anual_resultados_pct = []
    vpl_resultados = []

    for variacao_pct in variacoes_percentuais:
        fator = 1 + (variacao_pct / 100)
        receita_cenario = receita_mensal * fator
        fluxo_cenario = montar_fluxo_caixa(
            investimento_inicial, receita_cenario, custo_mensal, pro_labore
        )

        tir_mensal_cenario = calcular_tir_mensal(fluxo_cenario)
        tir_anual_cenario = calcular_tir_anual(tir_mensal_cenario)
        vpl_cenario = calcular_vpl(fluxo_cenario, taxa_mensal)

        variacoes.append(variacao_pct)
        tir_mensal_resultados_pct.append(
            tir_mensal_cenario * 100 if tir_mensal_cenario is not None else np.nan
        )
        tir_anual_resultados_pct.append(
            tir_anual_cenario * 100 if tir_anual_cenario is not None else np.nan
        )
        vpl_resultados.append(vpl_cenario)

    variacoes_validas = [
        v for v, t in zip(variacoes, tir_mensal_resultados_pct) if not np.isnan(t)
    ]
    tir_mensal_validas = [t for t in tir_mensal_resultados_pct if not np.isnan(t)]

    if len(variacoes_validas) >= 2:
        inclinacao_tir, _ = np.polyfit(variacoes_validas, tir_mensal_validas, 1)
    else:
        inclinacao_tir = 0.0

    inclinacao_vpl, _ = np.polyfit(variacoes, vpl_resultados, 1)

    return {
        "variacoes_percentuais": variacoes,
        "tir_mensal_resultante_pct": tir_mensal_resultados_pct,
        "tir_anual_resultante_pct": tir_anual_resultados_pct,
        "vpl_resultante": vpl_resultados,
        "inclinacao_tir": float(inclinacao_tir),
        "inclinacao_vpl": float(inclinacao_vpl),
    }


def classificar_risco(inclinacao_tir: float) -> str:
    """
    Classifica o risco do projeto a partir do modulo da inclinacao da reta
    de sensibilidade da TIR MENSAL (pontos percentuais de TIR mensal por
    1% de variacao na receita projetada).
    """
    inclinacao_abs = abs(inclinacao_tir)
    if inclinacao_abs < LIMIAR_RISCO_BAIXO:
        return "Baixo"
    if inclinacao_abs < LIMIAR_RISCO_MEDIO:
        return "Medio"
    return "Alto"


# ---------------------------------------------------------------------------
# Veredito final
# ---------------------------------------------------------------------------

def gerar_veredito(
    vpl: float,
    tir_anual: float | None,
    tma_anual: float,
    payback_simples_meses: float | None,
    periodo_meses: int,
    risco: str,
) -> dict:
    """
    Combina VPL, TIR x TMA, Payback e Risco em um veredito textual unico,
    junto com uma severidade ("positivo", "atencao" ou "negativo") usada
    para orientar a cor exibida na interface e no PDF.
    """
    projeto_viavel = vpl > 0 and tir_anual is not None and tir_anual > tma_anual
    payback_dentro_periodo = (
        payback_simples_meses is not None and payback_simples_meses <= periodo_meses
    )

    if not projeto_viavel:
        return {
            "titulo": "Projeto Inviavel nas Condicoes Atuais",
            "severidade": "negativo",
            "justificativa": (
                "O VPL e/ou a TIR anual nao superam a Taxa Minima de Atratividade "
                "definida, indicando que o projeto nao remunera o capital investido "
                "de forma satisfatoria nas premissas informadas."
            ),
        }

    if risco == "Alto":
        return {
            "titulo": "Projeto Viavel, porem de Alto Risco",
            "severidade": "atencao",
            "justificativa": (
                "O projeto e viavel nas premissas centrais (VPL positivo e TIR acima "
                "da TMA), mas a analise de sensibilidade mostra alta dependencia do "
                "resultado em relacao a variacoes de receita/fluxo de caixa. "
                "Recomenda-se cautela e planos de contingencia."
            ),
        }

    if not payback_dentro_periodo:
        return {
            "titulo": "Projeto Viavel, com Retorno de Capital Lento",
            "severidade": "atencao",
            "justificativa": (
                "O projeto e viavel financeiramente, porem o retorno do capital "
                "investido nao ocorre dentro do periodo analisado, o que aumenta a "
                "exposicao a riscos de longo prazo."
            ),
        }

    if risco == "Medio":
        return {
            "titulo": "Projeto Viavel - Risco Moderado",
            "severidade": "atencao",
            "justificativa": (
                "O projeto e viavel, com retorno acima da TMA e payback dentro do "
                "periodo analisado. A sensibilidade moderada da TIR indica a "
                "necessidade de acompanhamento das premissas de receita e custo."
            ),
        }

    return {
        "titulo": "Projeto Viavel e Recomendado",
        "severidade": "positivo",
        "justificativa": (
            "VPL positivo, TIR acima da TMA, payback dentro do periodo analisado e "
            "baixa sensibilidade a variacoes de receita/fluxo de caixa. O projeto "
            "apresenta condicoes financeiras favoraveis."
        ),
    }


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

def executar_analise(
    nome_projeto: str,
    tipo_projeto: str,
    tma_anual: float,
    periodo_meses: int,
    investimento_inicial: float,
    modo_fluxo: str,
    receita_media: float = 0.0,
    custo_medio: float = 0.0,
    pro_labore: float = 0.0,
    lancamentos_mensais: list[dict] | None = None,
    taxa_financiamento_anual: float | None = None,
    taxa_reinvestimento_anual: float | None = None,
) -> dict:
    """
    Executa a analise de viabilidade completa e retorna um dicionario com
    todos os resultados (fluxo de caixa, indicadores, sensibilidade, risco
    e veredito), pronto para ser consumido por app.py e reports.py.

    tma_anual, taxa_financiamento_anual e taxa_reinvestimento_anual devem
    ser informadas em fracao decimal (ex.: 0.15 para 15% a.a.). Quando as
    taxas de financiamento/reinvestimento nao sao informadas, assume-se
    que ambas sao iguais a TMA (premissa usual para a TIRM).
    """
    tma_mensal = taxa_anual_para_mensal(tma_anual)

    taxa_financiamento_anual = (
        tma_anual if taxa_financiamento_anual is None else taxa_financiamento_anual
    )
    taxa_reinvestimento_anual = (
        tma_anual if taxa_reinvestimento_anual is None else taxa_reinvestimento_anual
    )
    taxa_financiamento_mensal = taxa_anual_para_mensal(taxa_financiamento_anual)
    taxa_reinvestimento_mensal = taxa_anual_para_mensal(taxa_reinvestimento_anual)

    receita_mensal, custo_mensal = construir_componentes_mensais(
        periodo_meses=periodo_meses,
        modo=modo_fluxo,
        receita_media=receita_media,
        custo_medio=custo_medio,
        lancamentos_mensais=lancamentos_mensais,
    )
    fluxo_caixa = montar_fluxo_caixa(
        investimento_inicial, receita_mensal, custo_mensal, pro_labore
    )

    vpl = calcular_vpl(fluxo_caixa, tma_mensal)
    tir_mensal = calcular_tir_mensal(fluxo_caixa)
    tir_anual = calcular_tir_anual(tir_mensal)
    tirm_mensal = calcular_tirm_mensal(
        fluxo_caixa, taxa_financiamento_mensal, taxa_reinvestimento_mensal
    )
    tirm_anual = calcular_tirm_anual(tirm_mensal)
    pb_simples = payback_simples(fluxo_caixa)
    pb_descontado = payback_descontado(fluxo_caixa, tma_mensal)

    sensibilidade = analise_sensibilidade(
        investimento_inicial=investimento_inicial,
        receita_mensal=receita_mensal,
        custo_mensal=custo_mensal,
        pro_labore=pro_labore,
        taxa_mensal=tma_mensal,
    )
    risco = classificar_risco(sensibilidade["inclinacao_tir"])

    veredito = gerar_veredito(
        vpl=vpl,
        tir_anual=tir_anual,
        tma_anual=tma_anual,
        payback_simples_meses=pb_simples,
        periodo_meses=periodo_meses,
        risco=risco,
    )

    return {
        "nome_projeto": nome_projeto,
        "tipo_projeto": tipo_projeto,
        "tma_anual": tma_anual,
        "tma_mensal": tma_mensal,
        "periodo_meses": periodo_meses,
        "investimento_inicial": investimento_inicial,
        "modo_fluxo": modo_fluxo,
        "pro_labore": pro_labore,
        "fluxo_caixa": fluxo_caixa.tolist(),
        "vpl": vpl,
        "tir_mensal": tir_mensal,
        "tir_anual": tir_anual,
        "tirm_mensal": tirm_mensal,
        "tirm_anual": tirm_anual,
        "payback_simples_meses": pb_simples,
        "payback_descontado_meses": pb_descontado,
        "sensibilidade": sensibilidade,
        "risco": risco,
        "veredito": veredito,
    }
