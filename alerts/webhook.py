import requests
from config.settings import ALERT_WEBHOOK_URL

def send_webhook(message: str):
    if not ALERT_WEBHOOK_URL:
        return {"ok": False, "message": "ALERT_WEBHOOK_URL이 설정되지 않았습니다."}
    r = requests.post(ALERT_WEBHOOK_URL, json={"content": message, "text": message}, timeout=15)
    return {"ok": r.ok, "status_code": r.status_code, "message": r.text[:500]}
