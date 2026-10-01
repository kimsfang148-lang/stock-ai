import os
from dotenv import load_dotenv

load_dotenv()

# Local AI is the default. Public deployment never uses an operator-owned Gemini key.
AI_PROVIDER = os.getenv("AI_PROVIDER", "local").strip().lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")

DART_API_KEY = os.getenv("DART_API_KEY", "")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "StockAIPro/1.0 contact@example.com")

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_PROVIDER = os.getenv("NEWS_PROVIDER", "yfinance")

ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

DEFAULT_PERIOD = "5y"
RSI_PERIOD = 14
MA_FAST = 20
MA_MID = 60
MA_SLOW = 200
