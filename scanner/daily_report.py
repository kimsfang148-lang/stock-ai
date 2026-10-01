from datetime import datetime
from pathlib import Path
import pandas as pd
from scanner.daily_candidates import daily_candidates
from scanner.ranking import rank_candidates

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"

def build_daily_report(market="US", top_n=50):
    """Build and save a ranked daily scanner report. Returns (DataFrame, Path)."""
    rows = rank_candidates(daily_candidates(market), "장기점수")[:top_n]
    if not rows:
        return pd.DataFrame(), None
    df = pd.DataFrame(rows)
    df.insert(0, "순위", range(1, len(df) + 1))
    df["생성시각"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / f"daily_report_{market.lower()}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df, path
