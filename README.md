# Análise de Viabilidade Econômica

Aplicativo Streamlit para analisar investimentos usando fluxos de receitas e custos **mês a mês**.

## Executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Escolha de 1 a 240 meses, preencha investimento inicial, TMA anual e os valores da tabela mensal. Clique em **Calcular Viabilidade**. O botão *Carregar dados de exemplo* preenche 12 meses com um cenário demonstrativo.

A análise considera o fluxo mensal `receita - custo` e desconta as parcelas pela taxa mensal equivalente à TMA anual. Não há campo nem cálculo específico de Pró-Labore. Os resultados mostram VPL, TIR efetiva anual, TIRM efetiva anual, Payback Descontado e classificação de risco. O PDF inclui os indicadores e a tabela mensal.

Os pontos de interrogação ao lado dos indicadores abrem textos explicativos e o diagrama ilustrativo das faixas de sensibilidade da TIR. O ângulo é um indicador heurístico, **não** uma medida de probabilidade de perdas.