from data.dart_data import find_corp_code

def resolve_korean_corp_code(ticker: str):
    clean = str(ticker).strip().upper().replace(".KS", "").replace(".KQ", "")
    if not clean.isdigit():
        return None
    return find_corp_code(clean)
