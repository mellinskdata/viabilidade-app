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
            irr = npf.irr(cash_flows) #
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
        
    def generate_cash_flows(self, variation_factor=1.0):
        mode = self.data.get("mode", "average")
        inv = self.data.get("investimento", 0.0)
        pro_labore = self.data.get("pro_labore", 0.0)
        
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

    def _analyze_scenario(self, variation_factor=1.0):
        cfs = self.generate_cash_flows(variation_factor)
        tma_a = self.data.get("tma_anual", 0.0)
        tma_m = FinancialEngine.calc_tma_mensal(tma_a)
        
        vpl = FinancialEngine.calc_npv(tma_m, cfs)
        tir_m = FinancialEngine.calc_irr(cfs) #
        tir_a = ((1 + tir_m)**12 - 1) if tir_m is not None else None
        tirm_m = FinancialEngine.calc_mirr(cfs, tma_m, tma_m)
        payback_simples = FinancialEngine.calc_simple_payback(cfs)
        payback_desc = FinancialEngine.calc_discounted_payback(tma_m, cfs)
        
        return {
            "cfs": cfs, "tma_m": tma_m, "tma_a": tma_a,
            "vpl": vpl, "tir_m": tir_m, "tir_a": tir_a,
            "tirm_m": tirm_m,
            "payback_simples": payback_simples, 
            "payback_descontado": payback_desc
        }

    def analyze(self):
        base = self._analyze_scenario(1.0)
        
        # Análise de sensibilidade baseada no método do vídeo (linspace de -50% a +50%)
        sensibilidade = []
        variacoes = np.linspace(-0.5, 0.5, 20) #
        for var in variacoes:
            fator = 1.0 + var
            res = self._analyze_scenario(fator)
            sensibilidade.append({
                "variacao": float(var),
                "percentual": float(var * 100.0),
                "tir_m": res["tir_m"],
                "vpl": res["vpl"]
            })

        score = 0
        criterios = []
        
        if base["vpl"] > 0:
            score += 40
            criterios.append(("[APROVADO]", "VPL positivo"))
        else:
            criterios.append(("[REPROVADO]", "VPL negativo"))
            
        if base["tir_m"] is not None and base["tir_m"] >= base["tma_m"]:
            score += 40
            criterios.append(("[APROVADO]", "TIR superior ou igual à TMA"))
        else:
            criterios.append(("[REPROVADO]", "TIR inferior à TMA ou inexistente"))
            
        if base["payback_descontado"] is not None:
            score += 20
            criterios.append(("[APROVADO]", "Payback dentro do período"))
        else:
            criterios.append(("[REPROVADO]", "Investimento não recuperado"))
            
        score = max(0, min(100, score))
        
        if score >= 80: veredito = "APROVADO"
        elif score < 50: veredito = "REPROVADO"
        else: veredito = "REVISÃO RECOMENDADA"

        return {
            "nome": self.data.get("nome", "Projeto"),
            "tipo": self.data.get("tipo", "Futuro"),
            "base": base,
            "sensibilidade": sensibilidade,
            "score": score,
            "veredito": veredito,
            "criterios": criterios
        }
