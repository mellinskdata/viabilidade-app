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
    def calc_tirm(cash_flows: list, taxa_risco: float, taxa_seguranca: float):
        n = len(cash_flows) - 1
        if n <= 0: return None
        
        vp_negativos = 0.0
        vf_positivos = 0.0
        
        for t, cf in enumerate(cash_flows):
            if cf < 0:
                vp_negativos += abs(cf) / ((1 + taxa_seguranca) ** t)
            elif cf > 0:
                vf_positivos += cf * ((1 + taxa_risco) ** (n - t))
                
        if vp_negativos == 0 or vf_positivos == 0:
            return None
            
        return float((vf_positivos / vp_negativos) ** (1 / n) - 1)

    @staticmethod
    def calc_payback(cash_flows: list):
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
        tir_m = FinancialEngine.calc_irr(cfs)
        tir_a = ((1 + tir_m)**12 - 1) if tir_m is not None else None
        tirm_m = FinancialEngine.calc_tirm(cfs, tma_m, tma_m)
        payback = FinancialEngine.calc_payback(cfs)
        payback_desc = FinancialEngine.calc_discounted_payback(tma_m, cfs)
        
        return {
            "cfs": cfs, "tma_m": tma_m, "tma_a": tma_a,
            "vpl": vpl, "tir_m": tir_m, "tir_a": tir_a, "tirm_m": tirm_m,
            "payback": payback, "payback_desc": payback_desc
        }

    def analyze(self):
        base = self._analyze_scenario(1.0)
        tma_m = base["tma_m"]
        
        low, high = 0.0, 1.0
        fator_equilibrio = 1.0
        
        if base["vpl"] > 0:
            if self._analyze_scenario(0.0)["vpl"] < 0:
                for _ in range(50):
                    mid = (low + high) / 2.0
                    if self._analyze_scenario(mid)["vpl"] > 0:
                        high = mid
                    else:
                        low = mid
                fator_equilibrio = (low + high) / 2.0
            else:
                fator_equilibrio = 0.0
        else:
            fator_equilibrio = 1.0

        delta_x_pct = (1.0 - fator_equilibrio) * 100.0  
        
        angulo = 0.0
        if base["tir_m"] is not None and delta_x_pct > 0:
            tir_base_pct = base["tir_m"] * 100.0
            tma_pct = tma_m * 100.0
            delta_y = tir_base_pct - tma_pct
            
            if delta_y > 0:
                tan_alpha = delta_y / delta_x_pct
                angulo = math.degrees(math.atan(tan_alpha))

        limite_viabilidade = fator_equilibrio - 1.0

        if angulo < 30:
            risco = "BAIXO"
        elif angulo < 45:
            risco = "MÉDIO-BAIXO"
        elif angulo < 60:
            risco = "MÉDIO-ALTO"
        else:
            risco = "ALTO"

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
            
        if base["payback_desc"] is not None:
            score += 20
            criterios.append("Investimento recuperado no prazo")
        else:
            criterios.append("Investimento não recuperado")
            
        score = max(0, min(100, score))
        
        if score >= 80 and risco in ["BAIXO", "MÉDIO-BAIXO"]:
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
            "score": score,
            "veredito": veredito,
            "criterios": criterios
        }
