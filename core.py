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
        payback = FinancialEngine.calc_discounted_payback(tma_m, cfs)
        
        return {
            "cfs": cfs, "tma_m": tma_m, "tma_a": tma_a,
            "vpl": vpl, "tir_m": tir_m, "tir_a": tir_a,
            "payback": payback
        }

    def analyze(self):
        base = self._analyze_scenario(1.0)
        
        # Cenário com queda de 20% nas receitas (fator 0.8) para o coeficiente angular da reta
        cenario_20 = self._analyze_scenario(0.8)
        
        angulo = 0.0
        if base["tir_m"] is not None and cenario_20["tir_m"] is not None:
            delta_x = -0.2  # Variação no eixo X (-20%)
            delta_y = cenario_20["tir_m"] - base["tir_m"]  # Variação no eixo Y (TIR)
            if delta_x != 0:
                m = delta_y / delta_x  # Coeficiente angular m = delta_y / delta_x
                angulo = math.degrees(math.atan(abs(m)))

        # Limite de Viabilidade (Queda máxima suportada até VPL = 0)
        limite_viabilidade = 0.0
        if base["vpl"] > 0:
            # Varredura percentual de 0% até -100% (fator de 1.0 até 0.0)
            melhor_fator = 1.0
            for f in np.linspace(1.0, 0.0, 1000):
                res_f = self._analyze_scenario(f)
                if res_f["vpl"] >= 0:
                    melhor_fator = f
                else:
                    break
            # O limite é o quanto a receita pode cair (ex: se o VPL zera com fator 0.52, a queda limite é -48%)
            limite_viabilidade = melhor_fator - 1.0
        else:
            limite_viabilidade = 0.0 

        # Classificação de Risco baseada na margem de queda suportada
        queda_abs = abs(limite_viabilidade)
        if queda_abs >= 0.30:
            risco = "BAIXO"
        elif queda_abs >= 0.15:
            risco = "MÉDIO"
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
            "score": score,
            "veredito": veredito,
            "criterios": criterios
        }
