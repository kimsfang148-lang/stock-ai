from indicators.rsi import calculate_rsi
from indicators.macd import calculate_macd
from indicators.moving_average import add_moving_averages
from indicators.bollinger import add_bollinger

def add_indicators(df):
    df = df.copy()
    df = add_moving_averages(df)
    df = add_bollinger(df)
    df["RSI"] = calculate_rsi(df["Close"])
    df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(df["Close"])
    df["RET_1D"] = df["Close"].pct_change()
    df["RET_1M"] = df["Close"].pct_change(21)
    df["RET_3M"] = df["Close"].pct_change(63)
    df["RET_6M"] = df["Close"].pct_change(126)
    df["RET_1Y"] = df["Close"].pct_change(252)
    df["VOL_1Y"] = df["RET_1D"].rolling(252).std() * (252 ** 0.5)
    return df
