import numpy as np
import pandas as pd

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    prices = pd.to_numeric(prices, errors="coerce")
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder-style smoothing; works consistently with current pandas/numpy.
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # A completely flat series has RSI=50 rather than NaN after warm-up.
    flat = (avg_gain == 0) & (avg_loss == 0)
    rsi = rsi.mask(flat, 50.0)
    return rsi.clip(0, 100)
