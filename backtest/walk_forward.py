import pandas as pd
from backtest.engine import run_backtest
from backtest.performance import summarize

def walk_forward(df, initial_cash=10000, train_size=252, test_size=63):
    """Simple rolling out-of-sample walk-forward backtest."""
    if df is None or len(df) < train_size + test_size:
        return []
    rows = []
    start = 0
    while start + train_size + test_size <= len(df):
        train = df.iloc[start:start + train_size].copy()
        test = df.iloc[start + train_size:start + train_size + test_size].copy()
        if test.empty:
            break
        result = run_backtest(test, initial_cash=initial_cash)
        summary = summarize(result, initial_cash)
        rows.append({
            "train_start": str(train.index[0]),
            "train_end": str(train.index[-1]),
            "test_start": str(test.index[0]),
            "test_end": str(test.index[-1]),
            **summary,
        })
        start += test_size
    return rows
