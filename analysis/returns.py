import numpy as np

def period_returns(df):
    close = df["Close"].dropna()
    out = {}
    for name, days in [("1D",1),("1W",5),("1M",21),("3M",63),("6M",126),("1Y",252),("3Y",756),("5Y",1260)]:
        if len(close) > days:
            out[name] = float(close.iloc[-1] / close.iloc[-days-1] - 1)
    return out

def risk_metrics(df):
    r = df["Close"].pct_change().dropna()
    if r.empty:
        return {}
    wealth = (1+r).cumprod()
    peak = wealth.cummax()
    dd = wealth/peak - 1
    years = max(len(r)/252, 1/252)
    cagr = wealth.iloc[-1] ** (1/years) - 1
    vol = r.std() * np.sqrt(252)
    sharpe = (r.mean()*252) / vol if vol else np.nan
    return {
        "CAGR": float(cagr),
        "Volatility": float(vol),
        "MaxDrawdown": float(dd.min()),
        "Sharpe": float(sharpe) if np.isfinite(sharpe) else None,
    }
