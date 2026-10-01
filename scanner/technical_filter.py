from indicators.technical import add_indicators

def evaluate(ticker, df):
    df = add_indicators(df)
    if df.empty:
        return None, df
    row = df.iloc[-1]
    return {
        "ticker": ticker,
        "price": float(row["Close"]),
        "rsi": float(row["RSI"]) if row["RSI"] == row["RSI"] else None,
        "ma20": float(row["MA20"]) if row["MA20"] == row["MA20"] else None,
        "ma60": float(row["MA60"]) if row["MA60"] == row["MA60"] else None,
        "ma200": float(row["MA200"]) if row["MA200"] == row["MA200"] else None,
        "macd_bull": bool(row["MACD"] > row["MACD_SIGNAL"]) if row["MACD"] == row["MACD"] else False,
        "ret_1m": float(row["RET_1M"]) if row["RET_1M"] == row["RET_1M"] else None,
        "ret_1y": float(row["RET_1Y"]) if row["RET_1Y"] == row["RET_1Y"] else None,
    }, df
