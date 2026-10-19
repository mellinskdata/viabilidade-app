"""Textos e representação visual da ajuda contextual."""
import math

import matplotlib.pyplot as plt


TEXTOS_AJUDA = {
    "TMA": """**TMA (Taxa Mínima de Atratividade)**

**O que é:** O limite de rentabilidade para o seu dinheiro valer a pena.

A TMA representa o menor rendimento que você aceitaria para justificar um investimento, considerando o risco envolvido e as oportunidades disponíveis no mercado (como a poupança e a taxa Selic). Se um projeto rende menos do que a sua TMA, ele não é viável financeiramente.""",
    "VPL": """**VPL (Valor Presente Líquido)**

**O que é:** Quanto dinheiro o projeto coloca no seu bolso a valor de hoje.

O VPL traz todos os fluxos de caixa futuros de um investimento para o valor presente, utilizando a TMA como taxa de desconto.

- **VPL Positivo:** O projeto gera valor acima do esperado (ótimo negócio!).
- **VPL Negativo:** O projeto destrói valor e deve ser evitado.""",
    "TIR": """**TIR (Taxa Interna de Retorno)**

**O que é:** A taxa de juros percentual que o projeto promete entregar.

A TIR é a taxa que zera o VPL de um investimento. Em termos práticos, ela mostra a rentabilidade anual composta gerada pelo projeto. Para o investimento valer a pena, a TIR deve ser superior à TMA.""",
    "TIRM": """**TIRM (Taxa Interna de Retorno Modificada)**

**O que é:** Uma evolução mais realista da TIR tradicional.

A TIRM corrige as principais falhas da TIR comum, assumindo taxas realistas para o reinvestimento dos lucros obtidos ao longo do projeto. Apresenta uma taxa mais próxima do mercado.""",
    "PAYBACK": """**Payback Descontado**

**O que é:** O tempo que o dinheiro investido leva para voltar para o seu bolso.

Em outras palavras, é o tempo que leva para o resultado líquido do negócio pagar o valor que você investiu no começo. O diferencial do payback descontado é que ele considera a perda do valor do dinheiro ao longo do tempo, descontando os fluxos pela TMA. Não considera a inflação separadamente, a menos que ela esteja refletida na taxa usada.""",
    "CUSTOS": """**Custos**

Tudo o que você precisa pagar para manter a porta aberta e o produto pronto!

Para saber se o seu negócio realmente dá lucro, você precisa somar todas as despesas envolvidas na sua operação.

Veja o que entra nessa conta: matéria-prima e produtos, água, energia elétrica, gás, internet, taxas e impostos.

**Dica de ouro:** Nunca misture o dinheiro do seu bolso (pessoal) com o caixa do seu negócio.""",
    "RISCO": """**Análise de Risco — Sensibilidade da TIR**

**Resumo:** E se as coisas não saírem exatamente como o planejado?

A Sensibilidade da TIR simula o “e se...?” do seu negócio. Ela mostra o que acontece com a rentabilidade se algo fugir do planejado — como as vendas caírem 10% ou o preço da matéria-prima subir.

**Como ler o risco do seu projeto:** O gráfico abaixo é uma ilustração das faixas de ângulo entre RECEITAS (Vendas) e TIR, de acordo com o critério adotado por este aplicativo:""",
}


def figura_faixas_risco():
    """Diagrama conceitual inspirado no anexo fornecido; sem dados de projetos."""
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(-0.4, 10.6)
    ax.set_ylim(-0.4, 9.2)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.annotate("", xy=(10.1, 0), xytext=(0, 0), arrowprops={"arrowstyle": "-|>", "lw": 2.2, "color": "black", "mutation_scale": 20})
    ax.annotate("", xy=(0, 9), xytext=(0, 0), arrowprops={"arrowstyle": "-|>", "lw": 2.2, "color": "black", "mutation_scale": 20})
    ax.text(10.1, -0.25, "RECEITAS (Vendas)", fontsize=11, ha="right", va="top", weight="bold")
    ax.text(-0.3, 8.9, "TIR", fontsize=13, ha="right", weight="bold")
    for degrees, color, length in [(30, "#11a45e", 7.4), (45, "#1674bd", 6.7), (60, "#d22b26", 7.2)]:
        theta = math.radians(degrees)
        x, y = math.cos(theta) * length, math.sin(theta) * length
        ax.annotate("", xy=(x, y), xytext=(0, 0), arrowprops={"arrowstyle": "-|>", "lw": 1.8, "color": "black", "mutation_scale": 16})
        ax.text(x + 0.12, y + 0.12, f"{degrees}°", color=color, fontsize=17, weight="bold")
    fig.tight_layout(pad=0.8)
    return fig