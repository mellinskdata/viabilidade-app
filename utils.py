import re

def parse_brl(value_str) -> float:
    """Converte string (Ex: R$ 1.000,50 ou 1000,50) para float (1000.50)."""
    if not value_str or str(value_str).strip() == "":
        return 0.0
    
    if isinstance(value_str, (int, float)):
        return float(value_str)
        
    clean_str = re.sub(r'[^\d.,\-]', '', str(value_str))
    if not clean_str:
        return 0.0
        
    if ',' in clean_str:
        clean_str = clean_str.replace('.', '')
        clean_str = clean_str.replace(',', '.')
    
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def format_brl(value: float) -> str:
    """Formata float para R$ brasileiro."""
    if value is None:
        return "N/A"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(value: float) -> str:
    """Formata float para porcentagem brasileira."""
    if value is None:
        return "N/A"
    return f"{value * 100:,.2f}%".replace(".", ",")