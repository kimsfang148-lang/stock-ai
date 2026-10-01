def add_bollinger(df, period=20, std_mult=2):
    mid = df["Close"].rolling(period).mean()
    std = df["Close"].rolling(period).std()
    df["BB_MID"] = mid
    df["BB_UPPER"] = mid + std_mult * std
    df["BB_LOWER"] = mid - std_mult * std
    return df
