import yfinance as yf

def get_news(ticker: str, limit: int = 10):
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    out = []
    for item in items[:limit]:
        content = item.get("content", item)
        title = content.get("title") or item.get("title", "")
        pub = content.get("pubDate") or item.get("providerPublishTime", "")
        url = ""
        canonical = content.get("canonicalUrl") or {}
        if isinstance(canonical, dict):
            url = canonical.get("url", "")
        url = url or item.get("link", "")
        out.append({"title": title, "published": pub, "url": url})
    return out
