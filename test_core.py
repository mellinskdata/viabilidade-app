import io

import pytest
from core import FinancialEngine, ProjectAnalyzer
from reports import generate_pdf_buffer


def data(months=12, revenue=1000, cost=300, extra=None):
    d = {"nome": "Teste", "investimento": 1000.0, "tma_anual": 0.12,
         "dados_mensais": [{"receita": revenue, "custo": cost} for _ in range(months)]}
    if extra:
        d.update(extra)
    return d


def test_cash_flows_ignore_removed_pro_labore_and_average_options():
    engine = ProjectAnalyzer(data(2, 1000, 300, {"pro_labore": 9999, "mode": "average", "receita_media": 99999}))
    assert engine.generate_cash_flows() == [-1000, 700, 700]
    assert engine.generate_cash_flows(0.9) == [-1000, 600, 600]


def test_payback_discounted_uses_time_value_of_money():
    pb = FinancialEngine.calc_discounted_payback(0.1, [-100, 60, 60])
    assert pb == pytest.approx(1 + (100 - 60 / 1.1) / (60 / 1.1**2))
    assert FinancialEngine.calc_discounted_payback(0.1, [-100, 10, 10]) is None
    assert FinancialEngine.calc_discounted_payback(0, [-100, 100]) == pytest.approx(1)


def test_indicators_annualized_and_no_simple_payback():
    results = ProjectAnalyzer(data()).analyze()
    assert "payback_simples" not in results["base"]
    assert results["base"]["tir_a"] == pytest.approx((1 + results["base"]["tir_m"])**12 - 1)
    assert results["base"]["tirm_a"] == pytest.approx((1 + results["base"]["tirm_m"])**12 - 1)
    assert "tipo" not in results and "pl_solicitado" not in results


def test_no_return_project_and_pdf():
    results = ProjectAnalyzer(data(3, revenue=0, cost=400)).analyze()
    assert results["base"]["tir_m"] is None
    assert results["base"]["payback_descontado"] is None
    assert results["risco_classificacao"] == "INDEFINIDO"
    pdf = generate_pdf_buffer(results).getvalue()
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_months_and_pdf_dynamic():
    results = ProjectAnalyzer(data(24)).analyze()
    assert len(results["base"]["cfs"]) == 25
    assert len(results["dados_mensais"]) == 24
    assert generate_pdf_buffer(results).getvalue().startswith(b"%PDF")


def test_risk_bands_are_compatible_with_diagram():
    for angle, expected in [(30, "BAIXO"), (45, "MÉDIO BAIXO"), (60, "MÉDIO ALTO"), (61, "ALTO")]:
        assert ProjectAnalyzer.classify_risk(angle) == expected


def test_exemplo_40000_calculos_revisados():
    """Confere números do exemplo que o usuário carrega pelo botão."""
    from pathlib import Path
    app_source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert 'st.session_state["investimento"] = "40.000,00"' in app_source
    assert 'st.session_state["investimento"] = "29.400,00"' not in app_source
    assert 'st.button("?"' in app_source
    assert "st.dialog" in app_source
    assert 'format_pct(res[\'base\'][\'tir_m\'])' in app_source
    assert 'format_pct(res[\'base\'][\'tirm_m\'])' in app_source
    assert 'segundo os critérios do aplicativo' not in app_source
    example = {
        "nome": "Projeto Padrão (Exemplo)",
        "investimento": 40000,
        "tma_anual": .15,
        "dados_mensais": [{"receita": 10000, "custo": 4000} for _ in range(12)],
    }
    result = ProjectAnalyzer(example).analyze()
    assert result["base"]["vpl"] == pytest.approx(26804.46, abs=.01)
    assert result["base"]["tir_m"] == pytest.approx(.1045, abs=.0001)
    assert result["base"]["tir_a"] == pytest.approx(2.2953, abs=.0001)
    assert result["base"]["tirm_m"] == pytest.approx(.0559, abs=.0001)
    assert result["base"]["tirm_a"] == pytest.approx(.9206, abs=.0001)
    assert result["base"]["payback_descontado"] == pytest.approx(6.982, abs=.001)
    assert result["veredito"] == "APROVADO"


def test_pdf_contem_ajuda_e_taxas_mensais_sem_angulo():
    fitz = pytest.importorskip("fitz")
    result = ProjectAnalyzer({
        "nome": "Projeto Exemplo", "investimento": 40000, "tma_anual": .15,
        "dados_mensais": [{"receita": 10000, "custo": 4000} for _ in range(12)],
    }).analyze()
    pdf = fitz.open(stream=generate_pdf_buffer(result).getvalue(), filetype="pdf")
    text = "\n".join(page.get_text() for page in pdf)
    for expected in (
        "R$ 40.000,00", "R$ 26.804,46", "TIR mensal", "TIR anual",
        "TIRM mensal", "TIRM anual", "10,45%", "229,53%", "5,59%",
        "92,06%", "6,98 meses", "GUIA DOS INDICADORES", "?",
    ):
        assert expected in text, expected
    assert "ângulo" not in text.lower()
    assert "segundo os critérios do aplicativo" not in text.lower()
    assert "pró-labore" not in text.lower()
    assert sum(len(page.get_links()) for page in pdf) >= 8