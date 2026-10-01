import requests
from config.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    DART_API_KEY,
    SEC_USER_AGENT,
    NEWS_API_KEY,
    NEWS_PROVIDER,
    ALERT_WEBHOOK_URL,
    OLLAMA_URL,
    OLLAMA_MODEL,
    AI_PROVIDER,
)


def _ollama_status():
    try:
        r = requests.get(OLLAMA_URL.rstrip("/") + "/api/tags", timeout=3)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        installed = OLLAMA_MODEL in models or OLLAMA_MODEL.split(":")[0] in [m.split(":")[0] for m in models]
        if installed:
            return True, f"Ollama 연결됨 / 모델: {OLLAMA_MODEL}"
        return True, f"Ollama 연결됨 / {OLLAMA_MODEL} 미설치 (ollama pull 필요)"
    except Exception:
        return False, f"Ollama 미연결: {OLLAMA_URL}"


def get_connection_status():
    local_enabled, local_detail = _ollama_status()
    return {
        "로컬 AI (Ollama)": {"enabled": local_enabled, "detail": local_detail},
        "AI 기본 제공자": {"enabled": True, "detail": "Local" if AI_PROVIDER != "openai" else "OpenAI"},
        "OpenAI API": {"enabled": bool(OPENAI_API_KEY and OPENAI_MODEL), "detail": "키/모델 설정됨" if OPENAI_API_KEY and OPENAI_MODEL else "선택사항: 미설정"},
        "DART": {"enabled": bool(DART_API_KEY), "detail": "API 키 설정됨" if DART_API_KEY else "선택사항: API 키 필요"},
        "SEC": {"enabled": bool(SEC_USER_AGENT), "detail": "User-Agent 설정됨"},
        "News": {"enabled": bool(NEWS_PROVIDER), "detail": NEWS_PROVIDER},
        "Webhook": {"enabled": bool(ALERT_WEBHOOK_URL), "detail": "URL 설정됨" if ALERT_WEBHOOK_URL else "선택사항: 미설정"},
    }
