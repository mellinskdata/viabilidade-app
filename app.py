st.subheader("Indicadores Financeiros")
    base = res['base']
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("VPL", f"R$ {base['vpl']:,.2f}")
        st.metric("TIR Mensal", f"{base['tir_m']*100:.2f}%" if base['tir_m'] else "-")
        st.metric("TIR Anual", f"{base['tir_a']*100:.2f}%" if base['tir_a'] else "-")

    with col2:
        st.metric("TIRM Mensal", f"{base['tirm_m']*100:.2f}%" if base['tirm_m'] else "-")
        st.metric("Payback Simples", f"{base['payback']:.1f} meses" if base['payback'] is not None else "Não atinge")
        st.metric("Payback Descontado", f"{base['payback_desc']:.1f} meses" if base['payback_desc'] is not None else "Não atinge")

    with col3:
        st.metric("Queda Limite (Vendas)", f"{res['limite_viabilidade']*100:.1f}%")
        st.metric("Ângulo de Risco", f"{res['risco_angulo']:.1f}°")
        
    with col4:
        st.metric("Classificação de Risco", res['risco_classificacao'])
        st.metric("Veredito", res['veredito'])
