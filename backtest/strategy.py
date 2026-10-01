def buy_signal(row):
    required = ["Close","MA20","MA60","RSI","MACD","MACD_SIGNAL"]
    if any(k not in row or row[k] is None for k in required):
        return False
    return (
        row["Close"] > row["MA20"] > row["MA60"]
        and 40 <= row["RSI"] <= 65
        and row["MACD"] > row["MACD_SIGNAL"]
    )
