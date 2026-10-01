"""Resolve user-friendly stock names (including Korean names) to Yahoo Finance tickers."""
from __future__ import annotations

import re
from functools import lru_cache

import yfinance as yf

# Common aliases are kept local so the most common requests work even if Yahoo search is slow.
ALIASES = {
    # US
    "엔비디아": "NVDA", "nvidia": "NVDA", "엔비디아주식": "NVDA",
    "애플": "AAPL", "apple": "AAPL",
    "마이크로소프트": "MSFT", "microsoft": "MSFT",
    "아마존": "AMZN", "amazon": "AMZN",
    "알파벳": "GOOGL", "구글": "GOOGL", "google": "GOOGL",
    "메타": "META", "페이스북": "META", "facebook": "META",
    "테슬라": "TSLA", "tesla": "TSLA",
    "브로드컴": "AVGO", "broadcom": "AVGO",
    "amd": "AMD", "에이엠디": "AMD",
    "넷플릭스": "NFLX", "netflix": "NFLX",
    # KR
    "삼성전자": "005930.KS", "삼성전자우": "005935.KS",
    "sk하이닉스": "000660.KS", "하이닉스": "000660.KS",
    "네이버": "035420.KS", "naver": "035420.KS",
    "카카오": "035720.KS", "kakao": "035720.KS",
    "현대차": "005380.KS", "현대자동차": "005380.KS",
    "셀트리온": "068270.KS", "kb금융": "105560.KS",
}


def _clean(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _kr_code(value: str) -> str | None:
    compact = str(value).strip().upper().replace(".KS", "").replace(".KQ", "")
    if compact.isdigit() and len(compact) == 6:
        return compact + ".KS"
    return None


def infer_market(user_input: str) -> str:
    """Fast, network-free market guess used only for UI defaults."""
    raw = str(user_input or "").strip()
    upper = raw.upper()
    if upper.endswith((".KS", ".KQ")) or (raw.isdigit() and len(raw) == 6):
        return "KR"
    alias = ALIASES.get(_clean(raw))
    if alias and alias.endswith((".KS", ".KQ")):
        return "KR"
    return "US"


@lru_cache(maxsize=256)
def resolve_ticker(user_input: str, market: str = "US") -> tuple[str | None, str | None, str]:
    """Return (ticker, name, reason). Name may be a Yahoo/company display name."""
    raw = str(user_input or "").strip()
    if not raw:
        return None, None, "종목명 또는 종목코드를 입력하세요."
    market = market.upper()
    code = _kr_code(raw) if market == "KR" else None
    if code:
        return code, raw, "KRX 종목코드로 인식했습니다."

    key = _clean(raw)
    alias = ALIASES.get(key)
    if alias:
        if market == "KR" and not alias.endswith((".KS", ".KQ")):
            # A US alias should not be silently used in KR mode.
            pass
        elif market == "US" and alias.endswith((".KS", ".KQ")):
            pass
        else:
            return alias, raw, "저장된 한글/영문 종목명으로 인식했습니다."

    # Direct ticker input is accepted.
    direct = raw.upper()
    if market == "KR" and direct.endswith((".KS", ".KQ")):
        return direct, raw, "한국 주식 티커로 인식했습니다."
    if market == "US" and re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", direct):
        return direct, raw, "미국 주식 티커로 인식했습니다."

    # Yahoo search fallback for names not in the local alias table.
    try:
        result = yf.Search(raw, max_results=10)
        quotes = result.quotes or []
        for q in quotes:
            quote_type = str(q.get("quoteType", "")).upper()
            symbol = str(q.get("symbol", "")).upper()
            if quote_type not in {"EQUITY", "ETF"} or not symbol:
                continue
            is_kr = symbol.endswith((".KS", ".KQ"))
            if (market == "KR" and is_kr) or (market == "US" and not is_kr):
                name = q.get("longname") or q.get("shortname") or raw
                return symbol, name, "Yahoo Finance 종목 검색으로 찾았습니다."
    except Exception:
        pass

    return None, None, f"'{raw}'에 해당하는 {market} 종목을 찾지 못했습니다."
