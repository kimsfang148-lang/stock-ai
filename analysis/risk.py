def risk_flags(row, risk_metrics=None):
    flags = []
    rsi = row.get("RSI")
    if rsi is not None and rsi > 70:
        flags.append("RSI 과열 구간")
    if rsi is not None and rsi < 30:
        flags.append("RSI 과매도 구간")
    if row.get("Close",0) < row.get("MA200",0):
        flags.append("200일 이동평균선 하회")
    if risk_metrics and risk_metrics.get("MaxDrawdown") is not None and risk_metrics["MaxDrawdown"] < -0.30:
        flags.append("과거 최대낙폭 30% 초과")
    return flags
