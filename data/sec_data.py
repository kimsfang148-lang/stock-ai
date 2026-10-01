import requests
from config.settings import SEC_USER_AGENT

TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SUB_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

def _headers():
    return {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }

def ticker_map():
    r = requests.get(TICKER_URL, headers=_headers(), timeout=20)
    r.raise_for_status()
    raw = r.json()
    return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in raw.values()}

def get_cik(ticker: str):
    try:
        return ticker_map().get(ticker.upper().replace(".US", ""))
    except Exception:
        return None

def get_submissions(ticker: str, limit=20):
    cik = get_cik(ticker)
    if not cik:
        return {"cik": None, "filings": []}
    r = requests.get(SUB_URL.format(cik=cik), headers=_headers(), timeout=20)
    r.raise_for_status()
    data = r.json()
    recent = data.get("filings", {}).get("recent", {})
    rows = []
    keys = ["accessionNumber","filingDate","form","primaryDocument","primaryDocDescription"]
    n = min(limit, len(recent.get("form", [])))
    for i in range(n):
        row = {k: recent.get(k, [None]*n)[i] for k in keys}
        acc = (row["accessionNumber"] or "").replace("-", "")
        doc = row["primaryDocument"] or ""
        row["url"] = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}" if acc and doc else ""
        rows.append(row)
    return {"cik": cik, "filings": rows}

def get_company_facts(ticker: str):
    cik = get_cik(ticker)
    if not cik:
        return {}
    r = requests.get(FACTS_URL.format(cik=cik), headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()
