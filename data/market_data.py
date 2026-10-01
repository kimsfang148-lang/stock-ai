from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf


def normalize_yfinance_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance single/multi-index columns safely."""
    if df is None or df.empty:
        return df
    try:
        if isinstance(df.columns, pd.MultiIndex):
            fields = list(df.columns.get_level_values(0))
            tickers = list(df.columns.get_level_values(-1))
            if len(set(tickers)) == 1:
                df = df.copy()
                df.columns = fields
            else:
                df = df.copy()
                df.columns = ["_".join(str(x) for x in col if str(x)) for col in df.columns]
    except Exception:
        pass
    return df


_INTERVAL_RULES = {
    "1m": ("1m", None),
    "5m": ("5m", None),
    "10m": ("5m", "10min"),
    "15m": ("15m", None),
    "30m": ("30m", None),
    "60m": ("60m", None),
    "1h": ("60m", None),
    "1d": ("1d", None),
}


def _resolve_interval(interval: str):
    """Resolve UI interval to an upstream interval and optional resampling rule."""
    if interval in _INTERVAL_RULES:
        return _INTERVAL_RULES[interval]
    if isinstance(interval, str) and interval.startswith("custom:"):
        try:
            _, unit, raw_value = interval.split(":", 2)
            value = max(1, int(raw_value))
        except Exception:
            unit, value = "m", 5
        unit = unit.lower()
        if unit == "s":
            # Free upstream stock data is minute-level at best; seconds are approximated.
            return "1m", None
        if unit == "m":
            if value == 1:
                return "1m", None
            if value == 60:
                return "60m", None
            base = "5m" if value % 5 == 0 else "1m"
            return base, f"{value}min"
        if unit == "h":
            if value == 1:
                return "60m", None
            return "60m", f"{value}h"
        if unit == "d":
            if value == 1:
                return "1d", None
            return "1d", f"{value}D"
        if unit in {"mo", "month", "months"}:
            return "1d", f"{value}ME"
        if unit in {"y", "year", "years"}:
            return "1d", f"{value}YE"
    return interval, None


def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df is None or df.empty or not rule:
        return df
    agg = {
        "Open": "first", "High": "max", "Low": "min", "Close": "last",
        "Adj_Close": "last", "Volume": "sum",
    }
    available = {k: v for k, v in agg.items() if k in df.columns}
    if not available:
        return df
    try:
        out = df.resample(rule).agg(available).dropna(subset=["Open", "High", "Low", "Close"])
    except Exception:
        return df
    return out


def _custom_period_to_start(period: str):
    """Convert custom:<unit>:<value> into a timezone-aware UTC start datetime."""
    if not isinstance(period, str) or not period.startswith("custom:"):
        return None
    try:
        _, unit, raw_value = period.split(":", 2)
        value = max(1, int(raw_value))
    except Exception:
        return None
    unit = unit.lower()
    now = datetime.now(timezone.utc)
    if unit == "s":
        return now - timedelta(seconds=value)
    if unit == "m":
        return now - timedelta(minutes=value)
    if unit == "h":
        return now - timedelta(hours=value)
    if unit == "d":
        return now - timedelta(days=value)
    if unit in {"mo", "month", "months"}:
        return now - pd.DateOffset(months=value)
    if unit in {"y", "year", "years"}:
        return now - pd.DateOffset(years=value)
    return None


def _period_days(period: str) -> float | None:
    """Return requested period in days when it is a custom duration."""
    if not isinstance(period, str) or not period.startswith("custom:"):
        return None
    try:
        _, unit, raw = period.split(":", 2)
        value = max(1, int(raw))
    except Exception:
        return None
    unit = unit.lower()
    factors = {
        "s": 1 / 86400,
        "m": 1 / 1440,
        "h": 1 / 24,
        "d": 1,
        "mo": 30.4375,
        "month": 30.4375,
        "months": 30.4375,
        "y": 365.25,
        "year": 365.25,
        "years": 365.25,
    }
    return value * factors[unit] if unit in factors else None


def _bounded_fetch_window(period: str, fetch_interval: str):
    """Choose a provider-compatible window for Yahoo intraday history.

    Yahoo restricts how far back intraday bars can be requested. If the user asks
    for more history than the provider can supply, we fetch the largest practical
    window instead of returning an empty DataFrame.
    """
    days = _period_days(period)
    if days is None:
        return period, None

    # Practical Yahoo Finance limits for this app. Daily history is not capped here.
    if fetch_interval == "1m":
        max_days = 7
    elif fetch_interval in {"2m", "5m", "15m", "30m", "90m"}:
        max_days = 60
    elif fetch_interval in {"60m", "1h"}:
        max_days = 730
    else:
        return None, None

    actual_days = min(max(days, 1 / 1440), max_days)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=actual_days)
    return None, (start, end, days, actual_days, max_days)


def _download(ticker: str, fetch_interval: str, period: str):
    """Download data with provider-safe fallbacks."""
    custom_start = _custom_period_to_start(period)

    # Standard Yahoo periods work best when passed directly.
    if custom_start is None:
        fetch_period = period
        if fetch_interval != "1d":
            if fetch_interval == "1m":
                fetch_period = period if period in {"1d", "5d", "7d"} else "7d"
            elif fetch_interval in {"5m", "15m", "30m"}:
                fetch_period = period if period in {"1d", "5d", "1mo", "3mo"} else "60d"
            elif fetch_interval in {"60m", "1h"}:
                fetch_period = period if period in {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y"} else "2y"
        return yf.download(ticker, period=fetch_period, interval=fetch_interval, auto_adjust=False, progress=False)

    # Custom duration: cap intraday requests to a provider-supported window.
    safe_period, window = _bounded_fetch_window(period, fetch_interval)
    if safe_period is not None:
        return yf.download(ticker, period=safe_period, interval=fetch_interval, auto_adjust=False, progress=False)
    if window is None:
        # Daily/custom monthly/yearly history can use the exact requested start/end.
        start = custom_start.to_pydatetime() if hasattr(custom_start, "to_pydatetime") else custom_start
        return yf.download(ticker, start=start, end=datetime.now(timezone.utc), interval=fetch_interval, auto_adjust=False, progress=False)

    start, end, requested_days, actual_days, _ = window
    return yf.download(ticker, start=start, end=end, interval=fetch_interval, auto_adjust=False, progress=False)


def get_price_data(ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    """Fetch and normalize price history.

    The function never treats a provider historical-limit error as "invalid ticker".
    For intraday requests beyond Yahoo's supported history, it fetches the largest
    supported window so a valid ticker such as NVDA still returns usable data.
    """
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return pd.DataFrame()

    interval = interval or "1d"
    fetch_interval, resample_rule = _resolve_interval(interval)

    try:
        df = _download(ticker, fetch_interval, period)
    except Exception:
        # A second attempt with the most conservative valid query helps with
        # transient Yahoo/yfinance failures and timezone quirks.
        try:
            fallback_period = "7d" if fetch_interval == "1m" else ("60d" if fetch_interval in {"5m", "15m", "30m"} else "2y" if fetch_interval in {"60m", "1h"} else "5y")
            df = yf.download(ticker, period=fallback_period, interval=fetch_interval, auto_adjust=False, progress=False)
        except Exception:
            return pd.DataFrame()

    df = normalize_yfinance_columns(df)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"Adj Close": "Adj_Close"})
    df = df.dropna(how="all")
    if resample_rule:
        df = _resample_ohlcv(df, resample_rule)
    return df


def get_quote(ticker: str) -> dict:
    """Return a lightweight quote; price may be None when the provider blocks quote metadata."""
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = t.fast_info
    except Exception:
        pass
    price = None
    for key in ("last_price", "regularMarketPrice"):
        try:
            price = float(info[key])
            break
        except Exception:
            pass
    return {"price": price}
