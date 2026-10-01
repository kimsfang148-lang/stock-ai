def add_moving_averages(df, periods=(20,60,200)):
    for p in periods:
        df[f"MA{p}"] = df["Close"].rolling(p).mean()
    return df
