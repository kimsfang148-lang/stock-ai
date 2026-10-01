import yfinance as yf

def get_market_info(ticker: str):
    try:
        t = yf.Ticker(ticker)
        return t.info or {}
    except Exception:
        return {}

def get_quote(ticker: str):
    info = get_market_info(ticker)
    return {
        "ticker": ticker,
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap"),
    }
