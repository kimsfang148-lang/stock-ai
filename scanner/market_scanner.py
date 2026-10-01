from data.market_data import get_price_data
from scanner.technical_filter import evaluate
from analysis.score import score_horizons


def scan(tickers, period="2y"):
    rows, _ = scan_with_diagnostics(tickers, period=period)
    return rows


def scan_with_diagnostics(tickers, period="2y"):
    rows = []
    diagnostics = {"total": len(tickers), "data_empty": 0, "evaluation_failed": 0, "errors": [], "evaluated": 0}
    for ticker in tickers:
        try:
            df = get_price_data(ticker, period=period)
            if df is None or df.empty:
                diagnostics["data_empty"] += 1
                continue
            result, _ = evaluate(ticker, df)
            if not result:
                diagnostics["evaluation_failed"] += 1
                continue
            diagnostics["evaluated"] += 1
            r = {
                "Ticker": ticker,
                "Price": result["price"],
                "RSI": result["rsi"],
                "1M": result["ret_1m"],
                "1Y": result["ret_1y"],
                "MACD": "상승" if result["macd_bull"] else "하락",
            }
            scores = score_horizons({
                "Close": result["price"],
                "MA20": result["ma20"] or 0,
                "MA60": result["ma60"] or 0,
                "MA200": result["ma200"] or 0,
                "RSI": result["rsi"],
                "MACD": 1 if result["macd_bull"] else -1,
                "MACD_SIGNAL": 0,
                "BB_MID": result["ma20"] or 0,
            })
            r.update({"단기점수":round(scores["short"],1),"중기점수":round(scores["mid"],1),"장기점수":round(scores["long"],1)})
            rows.append(r)
        except Exception as e:
            diagnostics["errors"].append({"Ticker": ticker, "error": str(e)})
    return rows, diagnostics
