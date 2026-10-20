# Análise de Viabilidade Econômica

Aplicativo Streamlit para analisar investimentos usando fluxos de receitas e custos **mês a mês**.

## Executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Escolha de 1 a 240 meses, preencha investimento inicial, TMA anual e os valores da tabela mensal. Clique em **Calcular Viabilidade**. O botão *Carregar dados de exemplo* preenche 12 meses com um cenário demonstrativo.

A análise considera o fluxo mensal `receita - custo` e desconta as parcelas pela taxa mensal equivalente à TMA anual. Não há campo nem cálculo específico de Pró-Labore. Os resultados mostram VPL, TIR efetiva mensal e anual, TIRM efetiva mensal e anual, Payback Descontado e classificação de risco. O PDF inclui os indicadores, o glossário clicável e a tabela mensal.

Os botões **?** ao lado dos indicadores abrem janelas de ajuda, inclusive o diagrama ilustrativo das faixas de sensibilidade da TIR. No PDF, os **?** levam ao glossário de indicadores; nenhum ângulo numérico é exibido no resultado. O projeto de exemplo usa investimento de **R$ 40.000,00**, 12 meses de R$ 10.000,00 em receitas e R$ 4.000,00 em custos mensais, com TMA de 15% a.a.