"""Risk-based position sizing helpers.

The calculator keeps the fractional share result so users can see the
mathematical position size even when a broker only permits whole shares.
"""
from __future__ import annotations


def position_size(capital: float, entry_price: float, stop_price: float, risk_pct: float = 0.01) -> dict:
    capital = float(capital)
    entry_price = float(entry_price)
    stop_price = float(stop_price)
    risk_pct = float(risk_pct)
    if capital <= 0 or entry_price <= 0 or stop_price <= 0 or stop_price >= entry_price or risk_pct <= 0:
        return {
            "shares": 0.0,
            "whole_shares": 0,
            "risk_amount": 0.0,
            "position_value": 0.0,
            "risk_per_share": 0.0,
        }
    risk_amount = capital * risk_pct
    risk_per_share = entry_price - stop_price
    shares = risk_amount / risk_per_share
    whole_shares = int(shares)
    return {
        "shares": shares,
        "whole_shares": whole_shares,
        "risk_amount": risk_amount,
        "position_value": shares * entry_price,
        "whole_position_value": whole_shares * entry_price,
        "risk_per_share": risk_per_share,
    }
