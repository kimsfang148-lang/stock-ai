import json
from ai.analyst import analyze

CATEGORIES = ["Top 10", "관심", "관찰", "제외"]


def _compact_rows(rows, limit=50):
    compact = []
    for i, row in enumerate(rows[:limit], 1):
        compact.append({
            "rank": i,
            "ticker": row.get("종목") or row.get("Ticker") or row.get("ticker"),
            "score": row.get("장기점수") if row.get("장기점수") is not None else row.get("종합점수"),
            "trend": row.get("추세점수") or row.get("추세"),
            "momentum": row.get("모멘텀점수") or row.get("모멘텀"),
            "volume": row.get("거래량점수") or row.get("거래량"),
            "rsi": row.get("RSI"),
            "macd": row.get("MACD"),
            "price": row.get("Price") or row.get("현재가"),
        })
    return compact


def compare_top50(rows, provider="local"):
    """Compare up to 50 scanner rows with the configured AI provider.

    The AI must classify each ticker into Top 10 / 관심 / 관찰 / 제외 and
    provide evidence-based reasons. This is a decision-support summary, not
    a guarantee or investment recommendation.
    """
    compact = _compact_rows(rows, 50)
    if not compact:
        return "비교할 CSV/스캐너 데이터가 없습니다."

    prompt = {
        "task": "CSV 상위 종목 비교 분석",
        "rules": [
            "입력된 종목만 평가하고 새로운 종목을 만들지 말 것",
            "각 종목을 정확히 하나의 category로 분류: Top 10, 관심, 관찰, 제외",
            "Top 10은 최대 10개만 허용",
            "분류 근거는 점수, 추세, 모멘텀, 거래량, RSI, MACD 등 입력 데이터에 있는 값만 사용",
            "사실/데이터와 해석을 구분할 것",
            "데이터가 부족하면 추정하지 말고 '데이터 부족'이라고 표시할 것",
            "투자 수익을 보장하거나 확정적인 매수·매도 명령을 하지 말 것",
        ],
        "output_format": {
            "summary": "전체 50개(또는 입력 개수) 비교 요약",
            "groups": {
                "Top 10": [{"rank": 1, "ticker": "...", "reason": "...", "evidence": ["..."]}],
                "관심": [{"rank": 11, "ticker": "...", "reason": "...", "evidence": ["..."]}],
                "관찰": [{"rank": 20, "ticker": "...", "reason": "...", "evidence": ["..."]}],
                "제외": [{"rank": 30, "ticker": "...", "reason": "...", "evidence": ["..."]}],
            },
            "common_risks": ["..."],
            "data_gaps": ["..."],
        },
        "rows": compact,
    }
    return analyze(json.dumps(prompt, ensure_ascii=False), provider=provider)
