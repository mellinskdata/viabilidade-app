base = res['base']
    dados_tabela = [
        ["VPL", f"R$ {base['vpl']:,.2f}"],
        ["TIR Mensal", format_pct(base['tir_m'])],
        ["TIR Anual", format_pct(base['tir_a'])],
        ["TIRM Mensal", format_pct(base['tirm_m'])],
        ["Payback Simples", f"{base['payback']:.1f} meses" if base['payback'] is not None else "Não atinge"],
        ["Payback Descontado", f"{base['payback_desc']:.1f} meses" if base['payback_desc'] is not None else "Não atinge"],
        ["Queda Limite Suportada", format_pct(res['limite_viabilidade'])],
        ["Ângulo de Sensibilidade", f"{res['risco_angulo']:.2f}°"],
        ["Risco", res['risco_classificacao']],
        ["Score", f"{res['score']}/100"],
        ["Veredito", res['veredito']]
    ]
