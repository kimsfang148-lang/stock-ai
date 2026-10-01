"""Portfolio valuation helpers."""
from __future__ import annotations

import math

import yfinance as yf



def normalize_ticker(ticker: str, market: str) -> str:
    t = ticker.strip().upper()
    if market == "KR" and t.isdigit() and len(t) == 6:
        return t + ".KS"
    return t


def latest_price(ticker: str, market: str) -> float | None:
    t = normalize_ticker(ticker, market)
    try:
        info = yf.Ticker(t).fast_info
        for key in ("last_price", "regularMarketPrice"):
            try:
                value = float(info[key])
                if math.isfinite(value) and value > 0:
                    return value
            except Exception:
                pass
    except Exception:
        pass
    try:
        hist = yf.download(t, period="5d", interval="1d", auto_adjust=False, progress=False)
        if hist is None or hist.empty:
            return None
        close = hist["Close"]
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        value = float(close.dropna().iloc[-1])
        return value if math.isfinite(value) and value > 0 else None
    except Exception:
        return None


def build_portfolio_rows(holdings: list[dict]) -> list[dict]:
    rows = []
    for h in holdings:
        current = latest_price(h["ticker"], h["market"])
        shares = float(h["shares"])
        avg_cost = float(h["avg_cost"])
        invested = shares * avg_cost
        current_value = shares * current if current is not None else None
        pnl = current_value - invested if current_value is not None else None
        return_pct = pnl / invested if invested > 0 and pnl is not None else None
        rows.append({
            **h,
            "current_price": current,
            "invested": invested,
            "current_value": current_value,
            "pnl": pnl,
            "return_pct": return_pct,
            "currency": "KRW" if h["market"] == "KR" else "USD",
            "currency_display": "₩" if h["market"] == "KR" else "$",
        })
    return rows


def portfolio_summary(rows: list[dict]) -> dict:
    invested_krw = sum(r["invested"] for r in rows if r["market"] == "KR")
    value_krw = sum(r["current_value"] for r in rows if r["market"] == "KR" and r["current_value"] is not None)
    invested_usd = sum(r["invested"] for r in rows if r["market"] == "US")
    value_usd = sum(r["current_value"] for r in rows if r["market"] == "US" and r["current_value"] is not None)
    pnl_krw = value_krw - invested_krw
    pnl_usd = value_usd - invested_usd
    return {
        "KRW": {"invested": invested_krw, "value": value_krw, "pnl": pnl_krw, "return_pct": pnl_krw / invested_krw if invested_krw else None},
        "USD": {"invested": invested_usd, "value": value_usd, "pnl": pnl_usd, "return_pct": pnl_usd / invested_usd if invested_usd else None},
    }
