"""Currency helpers for the dashboard."""
from __future__ import annotations


def currency_for_market(market: str) -> tuple[str, str]:
    return ("KRW", "₩") if market.upper() == "KR" else ("USD", "$" )


def format_money(value, market: str, decimals: int = 2) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    code, symbol = currency_for_market(market)
    if code == "KRW":
        return f"{symbol}{number:,.0f} {code}"
    return f"{symbol}{number:,.{decimals}f} {code}"


def format_money_short(value, market: str) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    code, symbol = currency_for_market(market)
    abs_number = abs(number)
    if abs_number >= 1_000_000_000_000:
        text = f"{number / 1_000_000_000_000:.2f}T"
    elif abs_number >= 1_000_000_000:
        text = f"{number / 1_000_000_000:.2f}B"
    elif abs_number >= 1_000_000:
        text = f"{number / 1_000_000:.2f}M"
    elif abs_number >= 1_000:
        text = f"{number / 1_000:.2f}K"
    else:
        text = f"{number:,.0f}" if code == "KRW" else f"{number:,.2f}"
    return f"{symbol}{text} {code}"
