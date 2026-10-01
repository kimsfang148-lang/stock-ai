import pandas as pd
from backtest.strategy import buy_signal


def _row_date(index_value, fallback_pos=None):
    """Return a stable timestamp/date value for backtest records."""
    if isinstance(index_value, pd.Timestamp):
        return index_value
    try:
        return pd.Timestamp(index_value)
    except Exception:
        if fallback_pos is not None:
            return fallback_pos
        return index_value


def run_backtest(df, initial_cash=10000, stop_loss=-0.07, take_profit=0.15, fee=0.001):
    """Run the simple strategy backtest without assuming a named date index.

    Market-data providers can return a DatetimeIndex, a generic Index, or an
    index whose name is not ``date``.  The previous implementation stored the
    index values in a ``date`` column and then called ``set_index('date')``;
    when the input was empty or malformed this raised KeyError.  This version
    always builds the equity series with an explicit date column and handles
    empty/invalid input safely.
    """
    if df is None or df.empty or "Close" not in df.columns:
        empty = pd.DataFrame(columns=["equity"])
        empty.index = pd.DatetimeIndex([], name="date")
        return {
            "final_value": float(initial_cash),
            "return": 0.0,
            "trades": [],
            "equity": empty,
        }

    work = df.copy()
    work = work.loc[:, ~work.columns.duplicated()]
    work["Close"] = pd.to_numeric(work["Close"], errors="coerce")
    work = work.dropna(subset=["Close"])
    if work.empty:
        empty = pd.DataFrame(columns=["equity"])
        empty.index = pd.DatetimeIndex([], name="date")
        return {
            "final_value": float(initial_cash),
            "return": 0.0,
            "trades": [],
            "equity": empty,
        }

    cash = float(initial_cash)
    shares = 0.0
    entry = None
    trades = []
    equity = []

    for pos, (idx, row) in enumerate(work.iterrows()):
        price = float(row["Close"])
        event_date = _row_date(idx, pos)
        if shares == 0 and buy_signal(row):
            shares = (cash * (1 - fee)) / price
            cash = 0.0
            entry = price
            trades.append({"date": event_date, "action": "BUY", "price": price})
        elif shares > 0:
            ret = price / entry - 1
            sell = (
                ret <= stop_loss
                or ret >= take_profit
                or (row.get("MACD", 0) < row.get("MACD_SIGNAL", 0))
            )
            if sell:
                cash = shares * price * (1 - fee)
                trades.append({"date": event_date, "action": "SELL", "price": price, "return": ret})
                shares = 0.0
                entry = None
        equity.append({"date": event_date, "equity": cash + shares * price})

    if shares > 0:
        last = float(work["Close"].iloc[-1])
        last_date = _row_date(work.index[-1], len(work) - 1)
        cash = shares * last * (1 - fee)
        trades.append({"date": last_date, "action": "SELL_END", "price": last, "return": last / entry - 1})
        shares = 0.0

    # Explicitly create the date column. Never rely on the source index name.
    eq = pd.DataFrame(equity, columns=["date", "equity"])
    if not eq.empty:
        parsed_dates = pd.to_datetime(eq["date"], errors="coerce")
        if parsed_dates.notna().all():
            eq["date"] = parsed_dates
            eq = eq.set_index("date")
        else:
            # Keep a valid named index even for unusual provider indexes.
            eq.index = pd.RangeIndex(len(eq), name="date")
            eq = eq.drop(columns=["date"])
    else:
        eq = pd.DataFrame(columns=["equity"])
        eq.index = pd.DatetimeIndex([], name="date")

    final_value = float(eq["equity"].iloc[-1]) if not eq.empty else float(initial_cash)
    return {
        "final_value": final_value,
        "return": final_value / float(initial_cash) - 1,
        "trades": trades,
        "equity": eq,
    }
