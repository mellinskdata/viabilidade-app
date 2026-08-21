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
    def calc_discounted_payback(rate: float, cash_flows: list):
        accumulated = 0.0
        for t, cf in enumerate(cash_flows):
            discounted_cf = cf / ((1 + rate) ** t)
            prev_accumulated = accumulated
            accumulated += discounted_cf
            
            if accumulated >= 0 and t > 0:
                if discounted_cf == 0:
                    return t
                fraction = abs(prev_accumulated) / discounted_cf
                return (t - 1) + fraction
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
            fluxo_liq = self.data.get("fluxo_liquido_medio", 0.0) * variation_factor
            fluxo_mensal = fluxo_liq - pro_labore
            cfs.extend([fluxo_mensal] * meses)
        else:
            mensais = self.data.get("dados_mensais", [])
            for m in mensais:
                liq = m.get("fluxo_liquido", 0.0) * variation_factor
                cfs.append(liq - pro_labore)
                
        return cfs

    def _analyze_scenario(self, variation_factor=1.0, apply_pro_labore=False):
        cfs = self.generate_cash_flows(variation_factor, apply_pro_labore)
        tma_a = self.data.get("tma_anual", 0.0)
        tma_m = FinancialEngine.calc_tma_mensal(tma_a)
        
        vpl = FinancialEngine.calc_npv(tma_m, cfs)
        tir_m = FinancialEngine.calc_irr(cfs)
        tir_a = ((1 + tir_m)**12 - 1) if tir_m is not None else None
        payback = FinancialEngine.calc_discounted_payback(tma_m, cfs)
        
        return {
            "cfs": cfs, "tma_m": tma_m, "tma_a": tma_a,
            "vpl": vpl, "tir_m": tir_m, "tir_a": tir_a,
            "payback": payback
        }

    def analyze(self):
        base = self._analyze_scenario(1.0, False)
        
        cenario_20 = self._analyze_scenario(0.8, False)
        
        angulo = 0.0
        if base["tir_m"] is not None and cenario_20["tir_m"] is not None:
            delta_x = -0.2  
            delta_y = cenario_20["tir_m"] - base["tir_m"]  
            if delta_x != 0:
                m = delta_y / delta_x  
                angulo = math.degrees(math.atan(abs(m)))

        limite_viabilidade = None
        if base["vpl"] > 0:
            for factor in np.arange(1.0, -0.01, -0.01):
                res_limite = self._analyze_scenario(factor, False)
                if res_limite["vpl"] < 0:
                    limite_viabilidade = factor - 1.0
                    break
        elif base["vpl"] < 0:
            limite_viabilidade = 0.0 

        if limite_viabilidade is not None and abs(limite_viabilidade) >= 0.3:
            risco = "BAIXO"
        elif limite_viabilidade is not None and abs(limite_viabilidade) >= 0.15:
            risco = "MÉDIO"
        else:
            risco = "ALTO"

        pl_val = self.data.get("pro_labore", 0.0)
        pl_analise = None
        pl_recomendado = False
        if pl_val > 0:
            pl_analise = self._analyze_scenario(1.0, True)
            if pl_analise["vpl"] > 0 and (pl_analise["tir_m"] is not None and pl_analise["tir_m"] >= pl_analise["tma_m"]):
                pl_recomendado = True

        score = 0
        criterios = []
        
        if base["vpl"] > 0:
            score += 40
            criterios.append("VPL positivo (Gera Lucro)")
        else:
            criterios.append("VPL negativo")
            
        if base["tir_m"] is not None and base["tir_m"] >= base["tma_m"]:
            score += 40
            criterios.append("Rentabilidade superior à TMA")
        else:
            criterios.append("Rentabilidade abaixo da TMA")
            
        if base["payback"] is not None:
            score += 20
            criterios.append("Investimento recuperado no prazo")
        else:
            criterios.append("Investimento não recuperado")
            
        score = max(0, min(100, score))
        
        if score >= 80 and risco in ["BAIXO", "MÉDIO"]:
            veredito = "APROVADO"
        elif score < 50:
            veredito = "REPROVADO"
        else:
            veredito = "REVISÃO RECOMENDADA"

        return {
            "nome": self.data.get("nome", "Projeto"),
            "tipo": self.data.get("tipo", "Futuro"),
            "base": base,
            "risco_angulo": angulo,
            "risco_classificacao": risco,
            "limite_viabilidade": limite_viabilidade,
            "pl_cenario": pl_analise,
            "pl_recomendado": pl_recomendado,
            "score": score,
            "veredito": veredito,
            "criterios": criterios
        }
