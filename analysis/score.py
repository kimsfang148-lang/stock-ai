def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, float(x)))

def technical_score(row):
    s = 0
    if row.get("MA20", 0) > row.get("MA60", 0): s += 25
    if row.get("MA60", 0) > row.get("MA200", 0): s += 20
    rsi = row.get("RSI")
    if rsi is not None:
        if 45 <= rsi <= 65: s += 20
        elif 35 <= rsi <= 70: s += 12
    if row.get("MACD", 0) > row.get("MACD_SIGNAL", 0): s += 20
    if row.get("Close", 0) > row.get("BB_MID", 0): s += 15
    return clamp(s)

def score_horizons(row, fundamentals=None):
    fundamentals = fundamentals or {}
    tech = technical_score(row)
    growth = fundamentals.get("growth_score", 50)
    health = fundamentals.get("health_score", 50)
    valuation = fundamentals.get("valuation_score", 50)
    industry = fundamentals.get("industry_score", 50)
    disclosure = fundamentals.get("disclosure_score", 50)
    short = clamp(tech*0.70 + growth*0.10 + valuation*0.10 + disclosure*0.10)
    mid = clamp(tech*0.40 + growth*0.20 + health*0.15 + valuation*0.15 + industry*0.05 + disclosure*0.05)
    long = clamp(tech*0.10 + growth*0.30 + health*0.20 + valuation*0.20 + industry*0.15 + disclosure*0.05)
    return {"short": short, "mid": mid, "long": long}
