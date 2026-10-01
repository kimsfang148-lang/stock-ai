"""Command-line daily scanner helper.

Examples:
    python -m alerts.scheduler --market US
    python -m alerts.scheduler --market KR
"""
from __future__ import annotations

import argparse
from scanner.daily_candidates import daily_candidates
from scanner.ranking import rank_candidates
from scanner.daily_report import build_daily_report
from alerts.notification import format_daily_message
from alerts.webhook import send_webhook


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["US", "KR"], default="US")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--webhook", action="store_true")
    args = parser.parse_args()

    rows = rank_candidates(daily_candidates(args.market), min_long=0)[: args.top]
    print(format_daily_message(rows, args.top))
    df, path = build_daily_report(args.market, top_n=args.top)
    print(f"CSV: {path}" if path else "조건을 만족하는 후보가 없습니다.")
    if args.webhook and rows:
        print(send_webhook(format_daily_message(rows, args.top)))


if __name__ == "__main__":
    main()
