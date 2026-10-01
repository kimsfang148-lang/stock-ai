
def format_daily_message(rows, top_n=10):
    lines = ["📈 Stock AI Pro 오늘의 후보"]
    for i, r in enumerate(rows[:top_n], 1):
        lines.append(
            f"{i}. {r.get('Ticker')} | 장기 {r.get('장기점수')} | "
            f"중기 {r.get('중기점수')} | RSI {r.get('RSI')} | 1Y {r.get('1Y')}"
        )
    return "\n".join(lines)

# Email/Telegram/Discord/Slack connectors can call format_daily_message().
# They are intentionally kept separate from the scanner so they can be replaced later.
