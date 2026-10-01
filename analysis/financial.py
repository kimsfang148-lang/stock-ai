def basic_fundamental_scores(info: dict):
    # Conservative defaults when provider data is unavailable.
    profit = info.get("profitMargins")
    roe = info.get("returnOnEquity")
    debt = info.get("debtToEquity")
    pe = info.get("trailingPE")
    growth = info.get("revenueGrowth")
    growth_score = 50
    if growth is not None:
        growth_score = max(0, min(100, 50 + growth*100))
    health = 50
    if roe is not None:
        health += max(-20, min(25, roe*100/4))
    if debt is not None:
        health -= max(0, min(30, debt/10))
    valuation = 50
    if pe and pe > 0:
        valuation = max(10, min(90, 100 - pe*1.8))
    profit_score = 50 if profit is None else max(0, min(100, 50 + profit*100))
    return {
        "growth_score": growth_score,
        "health_score": health,
        "valuation_score": valuation,
        "industry_score": 50,
        "disclosure_score": 50,
        "profit_score": profit_score,
    }
