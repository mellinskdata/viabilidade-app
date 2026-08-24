import numpy as np
import numpy_financial as npf
import math

class FinancialEngine:
    @staticmethod
    def calc_tma_mensal(tma_anual: float) -> float:
        return (1 + tma_anual) ** (1/12) - 1

    @staticmethod
    def calc_npv(rate: float, cash_flows: list) -> float:
        return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))

    @staticmethod
    def calc_irr(cash_flows: list):
        try:
            irr = npf.irr(cash_flows)
            if irr is None or np.isnan(irr):
                return None
            return float(irr)
        except:
            return None

    @staticmethod
    def calc_mirr(cash_flows: list, finance_rate: float, reinvest_rate: float):
        try:
            mirr = npf.mirr(cash_flows, finance_rate, reinvest_rate)
            if mirr is None or np.isnan(mirr):
                return None
            return float(mirr)
        except:
            return None

    @staticmethod
    def calc_simple_payback(cash_flows: list):
        accumulated = 0.0
        for t, cf in enumerate(cash_flows):
            prev_accumulated = accumulated
            accumulated += cf
            
            if accumulated >= 0 and t > 0:
                if cf == 0:
                    return float(t)
                fraction = abs(prev_accumulated) / cf
                return float((t - 1) + fraction)
        return None

    @staticmethod
    def calc_discounted_payback(rate: float, cash_flows: list):
        accumulated = 0.0
        for t, cf in enumerate(cash_flows):
            discounted_cf = cf / ((1 + rate) ** t)
            prev_accumulated = accumulated
            accumulated += discounted_cf
            
            if accumulated >= 0 and t > 0:
                if discounted_cf == 0:
                    return float(t)
                fraction = abs(prev_accumulated) / discounted_cf
                return float((t - 1) + fraction)
        return None

class ProjectAnalyzer:
    def __init__(self, data: dict):
        self.data = data
        
    def generate_cash_flows(self, variation_factor=1.0, apply_pro_labore=False):
        mode = self.data.get("mode", "average")
        inv = self.data.get("investimento", 0.0)
        pro_labore = self.data.get("pro_labore", 0.0) if apply_pro_labore else 0.0
        
        cfs = [-inv]
        
        if mode == "average":
            meses = int(self.data.get("periodo_meses", 12))
            rec = self.data.get("receita_media", 0.0) * variation_factor
            cus = self.data.get("custo_medio", 0.0)
            fluxo_mensal = rec - cus - pro_labore
            cfs.extend([fluxo_mensal] * meses)
        else:
            mensais = self.data.get("dados_mensais", [])
            for m in mensais:
                rec = m.get("receita", 0.0) * variation_factor
                cus = m.get("custo", 0.0)
                cfs.append(rec - cus - pro_labore)
                
        return cfs

    def _analyze_scenario(self, variation_factor=1.0, apply_pro_labore=False):
        cfs = self.generate_cash_flows(variation_factor, apply_pro_labore)
        tma_a = self.data.get("tma_anual", 0.0)
        tma_m = FinancialEngine.calc_tma_mensal(tma_a)
        
        vpl = FinancialEngine.calc_npv(tma_m, cfs)
        tir_m = FinancialEngine.calc_irr(cfs)
        tir_a = ((1 + tir_m)**12 - 1) if tir_m is not None else None
        tirm_m = FinancialEngine.calc_mirr(cfs, tma_m, tma_m)
        tirm_a = ((1 + tirm_m)**12 - 1) if tirm_m is not None else None
        payback_simples = FinancialEngine.calc_simple_payback(cfs)
        payback_desc = FinancialEngine.calc_discounted_payback(tma_m, cfs)
        
        return {
            "cfs": cfs, "tma_m": tma_m, "tma_a": tma_a,
            "vpl": vpl, "tir_m": tir_m, "tir_a": tir_a,
            "tirm_m": tirm_m, "tirm_a": tirm_a, 
            "payback_simples": payback_simples, 
            "payback_descontado": payback_desc
        }

    def analyze(self):
        base = self._analyze_scenario(1.0, False)
        
        # 1. Sensibilidade
        sensibilidade = []
        fatores = [1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
        for f in fatores:
            res = self._analyze_scenario(f, False)
            sensibilidade.append({"variacao": f - 1.0, "tir_m": res["tir_m"], "vpl": res["vpl"]})
            
        # 2. Limite de Viabilidade (Busca Binaria - Interseccao Exata onde VPL zera)
        limite_viabilidade = None
        f_limit = 1.0
        
        if base["vpl"] > 0:
            low, high = 0.0, 1.0
            for _ in range(50):
                mid = (low + high) / 2.0
                if self._analyze_scenario(mid, False)["vpl"] > 0:
                    high = mid
                else:
                    low = mid
            f_limit = (low + high) / 2.0
            limite_viabilidade = 1.0 - f_limit
        elif base["vpl"] < 0:
            limite_viabilidade = 0.0
            f_limit = 1.0

        # 3. Risco Angular (Metodologia Prof. Carlos Roberto Ferreira)
        if base["tir_m"] is not None and limite_viabilidade is not None and limite_viabilidade > 0:
            # delta_y: variacao vertical em pontos percentuais (TIR base - TMA)
            delta_y = (base["tir_m"] * 100.0) - (base["tma_m"] * 100.0)
            # delta_x: variacao horizontal em pontos percentuais ate zerar o VPL (Queda limite)
            delta_x = limite_viabilidade * 100.0
            
            if delta_x > 0:
                m = delta_y / delta_x
                angulo = math.degrees(math.atan(m))
            else:
                angulo = 90.0
        else:
            angulo = None

        if angulo is None: risco = "INDEFINIDO"
        elif angulo < 30: risco = "BAIXO"
        elif angulo < 45: risco = "MEDIO"
        elif angulo < 60: risco = "ALTO"
        else: risco = "MUITO ALTO"

        # 4. Pro-Labore Analysis
        pl_val = self.data.get("pro_labore", 0.0)
        pl_analise = None
        pl_recomendado = False
        if pl_val > 0:
            pl_analise = self._analyze_scenario(1.0, True)
            if pl_analise["vpl"] > 0 and (pl_analise["tir_m"] is not None and pl_analise["tir_m"] >= pl_analise["tma_m"]):
                pl_recomendado = True

        # 5. Score e Veredito
        score = 0
        criterios = []
        
        if base["vpl"] > 0:
            score += 30
            criterios.append(("[APROVADO]", "VPL positivo"))
        else:
            criterios.append(("[REPROVADO]", "VPL negativo"))
            
        if base["tir_m"] is not None and base["tir_m"] >= base["tma_m"]:
            score += 30
            criterios.append(("[APROVADO]", "TIR superior ou igual a TMA"))
        else:
            criterios.append(("[REPROVADO]", "TIR inferior a TMA ou inexistente"))
            
        if base["payback_descontado"] is not None:
            score += 20
            criterios.append(("[APROVADO]", "Payback dentro do periodo analisado"))
        else:
            criterios.append(("[REPROVADO]", "Investimento nao recuperado no periodo"))
            
        risco_pontos = {"BAIXO": 20, "MEDIO": 10, "ALTO": 0, "MUITO ALTO": -10, "INDEFINIDO": 0}
        score += risco_pontos.get(risco, 0)
        score = max(0, min(100, score))
        
        if score >= 80: veredito = "APROVADO"
        elif score < 50: veredito = "REPROVADO"
        else: veredito = "REVISAO RECOMENDADA"

        return {
            "nome": self.data.get("nome", "Projeto"),
            "tipo": self.data.get("tipo", "Futuro"),
            "base": base, "sensibilidade": sensibilidade,
            "risco_angulo": angulo, "risco_classificacao": risco,
            "limite_viabilidade": limite_viabilidade,
            "pl_cenario": pl_analise, "pl_recomendado": pl_recomendado,
            "score": score, "veredito": veredito, "criterios": criterios
        }
