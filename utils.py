"""
utils.py
---------
Funcoes auxiliares de formatacao, cor e validacao compartilhadas entre
core.py, app.py e reports.py.

Mantidas neste modulo separado para evitar duplicacao de codigo e para que
tanto a interface Streamlit quanto o gerador de PDF usem exatamente a mesma
formatacao de numeros, moeda, percentuais e prazos.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Formatacao numerica (padrao brasileiro)
# ---------------------------------------------------------------------------

def formatar_moeda(valor: float | None, prefixo: str = "R$") -> str:
    """Formata um valor numerico como moeda no padrao brasileiro (R$ 1.234,56)."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "N/D"
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefixo} {texto}"


def formatar_percentual(valor: float | None, casas_decimais: int = 2) -> str:
    """
    Formata uma taxa em fracao decimal (ex.: 0.153) como percentual no
    padrao brasileiro (ex.: "15,30%"). Retorna "N/D" quando o indicador
    nao pode ser calculado (None ou NaN).
    """
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "N/D"
    percentual = valor * 100
    texto = f"{percentual:,.{casas_decimais}f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto}%"


def formatar_meses(valor: float | None) -> str:
    """Formata um numero de meses (payback) de forma legivel, com dias aproximados."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "Nao recuperado no periodo"
    meses_inteiros = int(valor)
    dias_fracao = round((valor - meses_inteiros) * 30)
    if dias_fracao >= 30:
        meses_inteiros += 1
        dias_fracao = 0
    if dias_fracao == 0:
        return f"{meses_inteiros} meses"
    return f"{meses_inteiros} meses e {dias_fracao} dias"


# ---------------------------------------------------------------------------
# Acesso seguro a dicionarios de resultado
# ---------------------------------------------------------------------------

def obter(dicionario: dict, chave: str, padrao=None):
    """
    Acesso seguro a um dicionario de resultados, sempre retornando um valor
    padrao e nunca lancando KeyError. Usado sobretudo em reports.py para
    blindar a geracao do PDF contra chaves ausentes ou resultados parciais.
    """
    if not isinstance(dicionario, dict):
        return padrao
    return dicionario.get(chave, padrao)


# ---------------------------------------------------------------------------
# Cores para severidade / risco (reaproveitadas na UI e no PDF)
# ---------------------------------------------------------------------------

def cor_severidade(severidade: str) -> str:
    """Mapeia a severidade do veredito para uma cor hexadecimal."""
    mapa = {
        "positivo": "#1B5E20",
        "atencao": "#E65100",
        "negativo": "#B71C1C",
    }
    return mapa.get(severidade, "#424242")


def rotulo_risco_para_cor(risco: str) -> str:
    """Mapeia o rotulo de risco (Baixo/Medio/Alto) para uma cor hexadecimal."""
    mapa = {
        "Baixo": "#1B5E20",
        "Medio": "#E65100",
        "Alto": "#B71C1C",
    }
    return mapa.get(risco, "#424242")


# ---------------------------------------------------------------------------
# Validacao de entradas do formulario
# ---------------------------------------------------------------------------

def validar_entradas_basicas(
    periodo_meses: int,
    investimento_inicial: float,
    tma_anual: float,
) -> list[str]:
    """
    Valida entradas basicas do formulario antes de acionar o motor de
    calculo. Retorna uma lista de mensagens de erro (lista vazia se tudo
    estiver correto).
    """
    erros: list[str] = []
    if periodo_meses is None or periodo_meses <= 0:
        erros.append("O periodo de analise deve ser maior que zero.")
    if investimento_inicial is None or investimento_inicial < 0:
        erros.append("O investimento inicial nao pode ser negativo.")
    if tma_anual is None or tma_anual <= -1:
        erros.append("A TMA anual informada e invalida.")
    return erros
