from scanner.market_scanner import scan

DEFAULT_US = ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","AVGO","TSLA","AMD","NFLX"]
DEFAULT_KR = ["005930.KS","000660.KS","035420.KS","035720.KS","005380.KS","068270.KS","105560.KS"]

def daily_candidates(market="US"):
    tickers = DEFAULT_US if market == "US" else DEFAULT_KR
    rows = scan(tickers)
    rows.sort(key=lambda x: x["장기점수"], reverse=True)
    return rows
