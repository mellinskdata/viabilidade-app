"""Motor financeiro para fluxos de caixa mensais (receitas menos custos)."""
import math

import numpy as np
import numpy_financial as npf


class FinancialEngine:
    @staticmethod
    def calc_tma_mensal(tma_anual: float) -> float:
        return (1 + tma_anual) ** (1 / 12) - 1

    @staticmethod
    def annualize_rate(rate):
        """Converte uma taxa efetiva mensal em efetiva anual."""
        return (1 + rate) ** 12 - 1 if rate is not None and rate >= -1 else None

    @staticmethod
    def calc_npv(rate: float, cash_flows: list) -> float:
        return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))

    @staticmethod
    def calc_irr(cash_flows: list):
        try:
            irr = npf.irr(cash_flows)
            if irr is None or not np.isfinite(irr):
                return None
            return float(irr)
        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    @staticmethod
    def calc_mirr(cash_flows: list, finance_rate: float, reinvest_rate: float):
        try:
            mirr = npf.mirr(cash_flows, finance_rate, reinvest_rate)
            if mirr is None or not np.isfinite(mirr):
                return None
            return float(mirr)
        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    @staticmethod
    def calc_discounted_payback(rate: float, cash_flows: list):
        """Retorna o mês fracionário em que o acumulado descontado fica não negativo."""
        accumulated = float(cash_flows[0])
        if accumulated >= 0:
            return 0.0
        for month, cf in enumerate(cash_flows[1:], start=1):
            discounted_cf = cf / ((1 + rate) ** month)
            previous = accumulated
            accumulated += discounted_cf
            if previous < 0 <= accumulated and discounted_cf > 0:
                return (month - 1) + (-previous / discounted_cf)
        return None


class ProjectAnalyzer:
    def __init__(self, data: dict):
        self.data = data

    def generate_cash_flows(self, variation_factor=1.0):
        """Investimento no momento zero e fluxos líquidos mensais subsequentes."""
        flows = [-float(self.data.get("investimento", 0.0))]
        for month in self.data.get("dados_mensais", []):
            revenue = float(month.get("receita", 0.0)) * variation_factor
            cost = float(month.get("custo", 0.0))
            flows.append(revenue - cost)
        return flows

    def _analyze_scenario(self, variation_factor=1.0):
        cfs = self.generate_cash_flows(variation_factor)
        tma_a = self.data.get("tma_anual", 0.0)
        tma_m = FinancialEngine.calc_tma_mensal(tma_a)
        tir_m = FinancialEngine.calc_irr(cfs)
        tirm_m = FinancialEngine.calc_mirr(cfs, tma_m, tma_m)
        return {
            "cfs": cfs,
            "tma_m": tma_m,
            "tma_a": tma_a,
            "vpl": FinancialEngine.calc_npv(tma_m, cfs),
            "tir_m": tir_m,
            "tir_a": FinancialEngine.annualize_rate(tir_m),
            "tirm_m": tirm_m,
            "tirm_a": FinancialEngine.annualize_rate(tirm_m),
            "payback_descontado": FinancialEngine.calc_discounted_payback(tma_m, cfs),
        }

    @staticmethod
    def classify_risk(angle):
        if angle is None or angle < 0:
            return "INDEFINIDO"
        if angle <= 30:
            return "BAIXO"
        if angle <= 45:
            return "MÉDIO BAIXO"
        if angle <= 60:
            return "MÉDIO ALTO"
        return "ALTO"

    def analyze(self):
        base = self._analyze_scenario()
        sensitivity = []
        for factor in [1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]:
            scenario = self._analyze_scenario(factor)
            sensitivity.append({
                "variacao": factor - 1.0,
                "tir_m": scenario["tir_m"],
                "vpl": scenario["vpl"],
            })

        # Queda proporcional máxima das receitas até VPL = 0, se o cenário for viável.
        viability_limit = None
        if base["vpl"] > 0:
            if self._analyze_scenario(0.0)["vpl"] >= 0:
                viability_limit = 1.0
            else:
                low, high = 0.0, 1.0
                for _ in range(50):
                    middle = (low + high) / 2
                    if self._analyze_scenario(middle)["vpl"] > 0:
                        high = middle
                    else:
                        low = middle
                viability_limit = 1.0 - (low + high) / 2
        elif base["vpl"] < 0:
            viability_limit = 0.0

        # Indicador angular legado: diferença TIR-TMA / limite de queda de receita.
        # Esta representação é uma heurística, não uma probabilidade de perdas.
        angle = None
        if base["tir_m"] is not None and viability_limit is not None and viability_limit > 0:
            delta_y = (base["tir_m"] - base["tma_m"]) * 100
            delta_x = viability_limit * 100
            angle = math.degrees(math.atan2(delta_y, delta_x))

        risk = self.classify_risk(angle)

        score = 0
        criteria = []
        if base["vpl"] > 0:
            score += 30
            criteria.append(("[APROVADO]", "VPL positivo"))
        else:
            criteria.append(("[REPROVADO]", "VPL não positivo"))

        if base["tir_m"] is not None and base["tir_m"] >= base["tma_m"]:
            score += 30
            criteria.append(("[APROVADO]", "TIR superior ou igual à TMA"))
        else:
            criteria.append(("[REPROVADO]", "TIR inferior à TMA ou inexistente"))

        if base["payback_descontado"] is not None:
            score += 20
            criteria.append(("[APROVADO]", "Payback descontado dentro do período"))
        else:
            criteria.append(("[REPROVADO]", "Investimento não recuperado no período"))

        score += {
            "BAIXO": 20, "MÉDIO BAIXO": 10, "MÉDIO ALTO": 0,
            "ALTO": -10, "INDEFINIDO": 0,
        }[risk]
        score = max(0, min(100, score))
        verdict = "APROVADO" if score >= 80 else "REPROVADO" if score < 50 else "REVISÃO RECOMENDADA"
        return {
            "nome": self.data.get("nome", "Projeto"),
            "base": base,
            "sensibilidade": sensitivity,
            "risco_angulo": angle,
            "risco_classificacao": risk,
            "limite_viabilidade": viability_limit,
            "score": score,
            "veredito": verdict,
            "criterios": criteria,
            "dados_mensais": self.data.get("dados_mensais", []),
        }