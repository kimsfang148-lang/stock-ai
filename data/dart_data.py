import requests
from config.settings import DART_API_KEY

BASE = "https://opendart.fss.or.kr/api"
DART_URL = f"{BASE}/fnlttSinglAcntAll.json"
CORP_URL = f"{BASE}/corpCode.json"
DISCLOSURE_URL = f"{BASE}/list.json"
INDEX_URL = f"{BASE}/fnlttSinglIndx.json"

def _check_key():
    if not DART_API_KEY:
        return {"enabled": False, "message": "DART_API_KEY가 설정되지 않았습니다."}
    return None

def get_corp_codes():
    err = _check_key()
    if err:
        return {"enabled": False, "rows": [], **err}
    r = requests.get(CORP_URL, params={"crtfc_key": DART_API_KEY}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return {"enabled": data.get("status") == "000", "message": data.get("message", ""), "rows": data.get("list", [])}

def find_corp_code(stock_code: str):
    result = get_corp_codes()
    if not result["enabled"]:
        return None
    code = str(stock_code).zfill(6)
    for row in result["rows"]:
        if str(row.get("stock_code", "")).zfill(6) == code:
            return row.get("corp_code")
    return None

def get_financials(corp_code: str, year: int, reprt_code="11011", fs_div="CFS"):
    err = _check_key()
    if err:
        return {"enabled": False, "rows": [], **err}
    params = {
        "crtfc_key": DART_API_KEY, "corp_code": corp_code,
        "bsns_year": year, "reprt_code": reprt_code, "fs_div": fs_div,
    }
    r = requests.get(DART_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return {"enabled": data.get("status") == "000", "message": data.get("message", ""), "rows": data.get("list", [])}

def get_key_indicators(corp_code: str, year: int, reprt_code="11011"):
    err = _check_key()
    if err:
        return {"enabled": False, "rows": [], **err}
    params = {
        "crtfc_key": DART_API_KEY, "corp_code": corp_code,
        "bsns_year": year, "reprt_code": reprt_code,
    }
    r = requests.get(INDEX_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return {"enabled": data.get("status") == "000", "message": data.get("message", ""), "rows": data.get("list", [])}

def get_disclosures(corp_code=None, bgn_de=None, end_de=None, page_no=1, page_count=20):
    err = _check_key()
    if err:
        return {"enabled": False, "rows": [], **err}
    params = {
        "crtfc_key": DART_API_KEY,
        "page_no": page_no, "page_count": page_count,
    }
    if corp_code:
        params["corp_code"] = corp_code
    if bgn_de:
        params["bgn_de"] = bgn_de
    if end_de:
        params["end_de"] = end_de
    r = requests.get(DISCLOSURE_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return {"enabled": data.get("status") == "000", "message": data.get("message", ""), "rows": data.get("list", [])}
