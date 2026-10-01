import yfinance as yf

PEERS = {
    "AAPL": ["MSFT","GOOGL","AMZN"],
    "MSFT": ["AAPL","GOOGL","AMZN"],
    "NVDA": ["AMD","AVGO","TSM"],
    "TSLA": ["F","GM","RIVN"],
    "005930.KS": ["000660.KS","009150.KS"],
}

def get_peers(ticker):
    peers = PEERS.get(ticker.upper(), [])
    rows = []
    for p in peers:
        try:
            i = yf.Ticker(p).info
            rows.append({"ticker":p, "pe":i.get("trailingPE"), "market_cap":i.get("marketCap")})
        except Exception:
            rows.append({"ticker":p, "pe":None, "market_cap":None})
    return rows
