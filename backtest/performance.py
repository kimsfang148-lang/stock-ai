import numpy as np
import pandas as pd


def summarize(result, initial_cash):
    """Summarize a backtest safely, including empty/invalid equity results."""
    initial_cash = float(initial_cash or 0)
    equity_obj = (result or {}).get("equity")

    if isinstance(equity_obj, pd.DataFrame) and "equity" in equity_obj.columns:
        eq = pd.to_numeric(equity_obj["equity"], errors="coerce").dropna()
    elif isinstance(equity_obj, pd.Series):
        eq = pd.to_numeric(equity_obj, errors="coerce").dropna()
    else:
        eq = pd.Series(dtype=float)

    ret = float((result or {}).get("return", 0.0) or 0.0)
    if eq.empty:
        final_value = initial_cash
        cagr = 0.0
        max_drawdown = 0.0
    else:
        final_value = float(eq.iloc[-1])
        daily = eq.pct_change().dropna()
        years = max(len(daily) / 252, 1 / 252)
        cagr = ((final_value / initial_cash) ** (1 / years) - 1) if initial_cash > 0 else 0.0
        dd = eq / eq.cummax() - 1
        max_drawdown = float(dd.min()) if not dd.empty else 0.0

    trades = (result or {}).get("trades", []) or []
    sells = [x for x in trades if x.get("action") in ("SELL", "SELL_END") and "return" in x]
    wins = [x for x in sells if x.get("return", 0) > 0]

    return {
        "Total Return": ret,
        "CAGR": cagr,
        "Max Drawdown": max_drawdown,
        "Win Rate": len(wins) / len(sells) if sells else None,
        "Trades": len(sells),
        "Final Value": final_value,
    }
