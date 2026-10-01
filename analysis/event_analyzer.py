from __future__ import annotations

from ai.analyst import analyze


def _compact(items, fields):
    out = []
    for item in items[:10]:
        out.append({field: item.get(field, "") for field in fields})
    return out


def analyze_news_events(ticker: str, news_items: list[dict], provider: str = "local") -> str:
    payload = {
        "task": "뉴스 이벤트 분석",
        "ticker": ticker,
        "items": _compact(news_items, ["title", "published", "url"]),
        "instructions": "각 뉴스의 핵심 내용, 긍정/중립/부정 가능성, 실적·밸류에이션·주가에 영향을 줄 수 있는 경로, 추가 확인사항을 구분해서 설명하라. 확정 사실과 추정/해석을 구분하라.",
    }
    return analyze(payload, provider=provider)


def analyze_disclosure_events(ticker: str, disclosures: list[dict], provider: str = "local") -> str:
    payload = {
        "task": "기업 공시 이벤트 분석",
        "ticker": ticker,
        "items": _compact(disclosures, ["filingDate", "form", "report_nm", "corp_name", "rcept_dt", "rcept_no", "primaryDocDescription", "url"]),
        "instructions": "공시별 핵심 사실과 투자자가 확인해야 할 숫자/조건을 요약하고, 주가에 영향을 줄 수 있는 요인을 긍정/중립/부정 가능성으로 구분하라. 사실과 해석을 구분하고 원문 확인이 필요한 부분을 표시하라.",
    }
    return analyze(payload, provider=provider)
