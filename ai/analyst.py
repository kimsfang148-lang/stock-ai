from __future__ import annotations

import json
import os
import requests

from config.settings import (
    AI_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_URL,
    OLLAMA_MODEL,
)
from ai.prompts import SYSTEM_PROMPT


def _get_user_gemini_key():
    """Return only the key entered by the current user in this Streamlit session.

    No server-side Gemini key is read. This keeps the public deployment from
    spending the app owner's API quota.
    """
    try:
        import streamlit as st
        return str(st.session_state.get("user_gemini_api_key", "")).strip()
    except Exception:
        return ""


def _analyze_gemini(payload, key=None):
    key = (key or _get_user_gemini_key()).strip()
    if not key:
        return (
            "Gemini API 키가 없습니다.\n\n"
            "공용 웹앱에서 운영자 키는 사용하지 않습니다. 본인의 Gemini API 키를 "
            "사이드바에 직접 입력하면 그 세션에서만 사용됩니다.\n"
            "키를 입력하지 않아도 '무료 규칙 기반 분석'은 사용할 수 있습니다."
        )

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": str(payload)}]}],
        "generationConfig": {"temperature": 0.2},
    }
    response = requests.post(url, params={"key": key}, json=body, timeout=120)
    if not response.ok:
        detail = response.text[:1000]
        return f"Gemini AI 분석 오류: HTTP {response.status_code}\n{detail}"
    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return "Gemini가 분석 결과를 반환하지 않았습니다. 본인 키의 무료 사용 한도를 확인하세요."
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(str(p.get("text", "")) for p in parts if p.get("text")).strip()
    return text or "Gemini가 빈 응답을 반환했습니다."


def _analyze_ollama(payload):
    url = OLLAMA_URL.rstrip("/") + "/api/chat"
    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(payload)},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = requests.post(url, json=body, timeout=180)
    response.raise_for_status()
    data = response.json()
    return data.get("message", {}).get("content", "").strip() or "로컬 AI가 빈 응답을 반환했습니다."


def _analyze_openai(payload):
    if not OPENAI_API_KEY or not OPENAI_MODEL:
        return "운영자 OpenAI API 키는 공용 배포에서 사용하지 않도록 설정되어 있습니다."
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=str(payload),
    )
    return response.output_text


def _fmt_pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "-"


def _free_rules(payload):
    """Zero-cost deterministic analysis for public deployments.

    It never calls an external AI service and is intentionally presented as a
    rules-based summary, not as an AI-generated opinion.
    """
    raw = payload
    if isinstance(payload, str):
        try:
            raw = json.loads(payload)
        except Exception:
            raw = {"text": payload}

    if isinstance(raw, dict) and raw.get("task") in {"뉴스 이벤트 분석", "기업 공시 이벤트 분석"}:
        ticker = raw.get("ticker", "종목")
        items = raw.get("items") or []
        lines = [f"### {raw.get('task')} — {ticker}", "", "무료 규칙 기반 요약입니다. 원문 확인이 필요합니다.", ""]
        if not items:
            lines.append("확인 가능한 항목이 없습니다.")
        else:
            for i, item in enumerate(items[:10], 1):
                title = item.get("title") or item.get("report_nm") or item.get("form") or "항목"
                date = item.get("published") or item.get("filingDate") or item.get("rcept_dt") or ""
                lines.append(f"**{i}. {title}** {f'({date})' if date else ''}")
                if item.get("url"):
                    lines.append(f"- 원문: {item['url']}")
            lines += ["", "※ 이 요약은 제목/메타데이터 중심이며 기사·공시 원문 전체를 해석한 결과가 아닙니다."]
        return "\n".join(lines)

    if isinstance(raw, dict) and "rows" in raw and isinstance(raw.get("rows"), list):
        rows = raw["rows"]
        scored = []
        for row in rows:
            vals = []
            for key in ("score", "total_score", "overall_score", "reference_score"):
                try:
                    vals.append(float(row.get(key)))
                except Exception:
                    pass
            if vals:
                scored.append((sum(vals) / len(vals), row))
        scored.sort(key=lambda x: x[0], reverse=True)
        lines = ["### 상위 종목 무료 규칙 기반 비교", "", f"입력 종목 수: {len(rows)}"]
        if scored:
            lines.append("\n점수 필드가 확인되는 종목을 내림차순으로 표시합니다.")
            for i, (_, row) in enumerate(scored[:10], 1):
                ticker = row.get("ticker") or row.get("symbol") or row.get("name") or "-"
                lines.append(f"{i}. **{ticker}** — {row.get('reason') or row.get('score') or '점수 데이터 확인'}")
        else:
            lines.append("비교 가능한 점수 필드가 없어 원자료를 기준으로 판단할 수 없습니다.")
        return "\n".join(lines)

    ticker = raw.get("ticker", "종목") if isinstance(raw, dict) else "종목"
    lines = [f"### {ticker} 무료 종합분석", "", "**AI가 아닌 규칙 기반 요약**입니다. 별도 API 비용이 발생하지 않습니다."]
    if not isinstance(raw, dict):
        return "\n".join(lines + ["입력 자료를 구조화해서 해석할 수 없습니다."])

    try:
        price = float(raw.get("current_price"))
        lines.append(f"- 현재가: {price:,.2f}")
    except Exception:
        pass
    scores = raw.get("scores") or {}
    if scores:
        lines.append(f"- 참고점수: {scores}")
    returns = raw.get("returns") or {}
    if returns:
        lines.append(f"- 수익률 지표: {returns}")
    risks = raw.get("risk_metrics") or {}
    if risks:
        lines.append(f"- 위험 지표: {risks}")
    try:
        rsi = float(raw.get("rsi"))
        zone = "과매수 가능성" if rsi >= 70 else "과매도 가능성" if rsi <= 30 else "중립 구간"
        lines.append(f"- RSI: {rsi:.1f} ({zone})")
    except Exception:
        pass
    lines.append(f"- MACD 상태: {'상승 방향' if raw.get('macd_bull') else '하락/중립 방향'}")
    if raw.get("fair_value") is not None:
        lines.append(f"- 모델 참고 적정가치: {raw.get('fair_value')}")
    if raw.get("risk_flags"):
        lines.append(f"- 위험 신호: {raw.get('risk_flags')}")
    lines += ["", "※ 투자판단을 대신하지 않으며, 수치와 원자료를 확인한 뒤 판단하세요."]
    return "\n".join(lines)


def analyze(payload, provider=None):
    """Analyze locally, with a user-supplied cloud key, or with zero-cost rules."""
    selected = (provider or AI_PROVIDER or "local").lower().strip()
    if selected in {"gemini", "gemini_user"}:
        return _analyze_gemini(payload)
    if selected == "free_rules":
        return _free_rules(payload)
    if selected == "openai":
        try:
            return _analyze_openai(payload)
        except Exception as e:
            return f"OpenAI AI 분석 오류: {e}"

    try:
        return _analyze_ollama(payload)
    except requests.exceptions.ConnectionError:
        return (
            "로컬 AI(Ollama)에 연결할 수 없습니다.\n\n"
            "공용 웹에서는 사용자 PC의 Ollama를 사용할 수 없습니다. "
            "사이드바에서 '사용자 Gemini API'를 선택하거나 '무료 규칙 기반 분석'을 사용하세요."
        )
    except requests.exceptions.HTTPError as e:
        detail = getattr(e.response, "text", "")[:500]
        return f"로컬 AI(Ollama) 오류: {e}\n{detail}"
    except Exception as e:
        return f"로컬 AI 분석 오류: {e}"


def test_connection(provider=None):
    selected = (provider or AI_PROVIDER or "local").lower().strip()
    if selected in {"gemini", "gemini_user"}:
        try:
            result = _analyze_gemini({"test": "connection", "message": "Return only: CONNECTED"})
            return ("Gemini AI 분석 오류" not in result and "API 키가 없습니다" not in result), result
        except Exception as e:
            return False, str(e)
    if selected == "free_rules":
        return True, "외부 API를 사용하지 않는 무료 규칙 기반 분석이 준비되어 있습니다."
    if selected == "openai":
        try:
            result = _analyze_openai({"test": "connection", "message": "Return only: CONNECTED"})
            return True, result
        except Exception as e:
            return False, str(e)
    try:
        result = _analyze_ollama({"test": "connection", "message": "Return only: CONNECTED"})
        return True, result
    except Exception as e:
        return False, e
