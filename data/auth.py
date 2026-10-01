"""Local account management and portfolio storage for Stock AI Pro."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from pathlib import Path

from data.migration import migrate_legacy_database

DB_PATH = Path(__file__).resolve().parent / "stock_ai_accounts.db"
# On first use, safely copy an older local DB if one is found beside this project.
_migrate_result = migrate_legacy_database()
ITERATIONS = 310_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


def _merge_duplicate_holdings(conn: sqlite3.Connection) -> None:
    """Merge duplicate positions by account + ticker + market using weighted average cost."""
    groups = conn.execute(
        "SELECT user_id, ticker, market, COUNT(*) AS n FROM portfolio_holdings "
        "GROUP BY user_id, ticker, market HAVING COUNT(*) > 1"
    ).fetchall()
    for user_id, ticker, market, _ in groups:
        rows = conn.execute(
            "SELECT id, shares, avg_cost FROM portfolio_holdings "
            "WHERE user_id=? AND ticker=? AND market=? ORDER BY id",
            (user_id, ticker, market),
        ).fetchall()
        total_shares = sum(float(r[1]) for r in rows)
        total_cost = sum(float(r[1]) * float(r[2]) for r in rows)
        if total_shares <= 0:
            continue
        weighted_avg = total_cost / total_shares
        keep_id = rows[0][0]
        conn.execute(
            "UPDATE portfolio_holdings SET shares=?, avg_cost=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (total_shares, weighted_avg, keep_id),
        )
        conn.executemany(
            "DELETE FROM portfolio_holdings WHERE id=?",
            [(r[0],) for r in rows[1:]],
        )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS watchlists (
            user_id INTEGER PRIMARY KEY,
            tickers TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            market TEXT NOT NULL CHECK(market IN ('US','KR')),
            shares REAL NOT NULL CHECK(shares > 0),
            avg_cost REAL NOT NULL CHECK(avg_cost > 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )"""
    )
    _merge_duplicate_holdings(conn)
    conn.commit()
    return conn


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def validate_registration(username: str, password: str, display_name: str) -> str | None:
    if not USERNAME_RE.fullmatch(username.strip()):
        return "아이디는 영문/숫자/._-만 사용해 3~30자로 입력하세요."
    if len(password) < 6:
        return "비밀번호는 6자 이상이어야 합니다."
    if not display_name.strip():
        return "표시 이름을 입력하세요."
    if len(display_name.strip()) > 40:
        return "표시 이름은 40자 이하로 입력하세요."
    return None


def create_account(username: str, password: str, display_name: str) -> tuple[bool, str]:
    username = username.strip()
    display_name = display_name.strip()
    error = validate_registration(username, password, display_name)
    if error:
        return False, error
    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)
    try:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO users(username, display_name, salt, password_hash) VALUES(?,?,?,?)",
                (username, display_name, salt, password_hash),
            )
            user_id = cur.lastrowid
            conn.execute("INSERT INTO watchlists(user_id, tickers) VALUES(?, '')", (user_id,))
        return True, "계정이 생성되었습니다. 로그인해 주세요."
    except sqlite3.IntegrityError:
        return False, "이미 존재하는 아이디입니다."


def authenticate(username: str, password: str) -> dict | None:
    username = username.strip()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, display_name, salt, password_hash FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
    if not row:
        return None
    user_id, db_username, display_name, salt, stored_hash = row
    candidate = _hash_password(password, salt)
    if not hmac.compare_digest(candidate, stored_hash):
        return None
    return {"id": user_id, "username": db_username, "display_name": display_name}


def get_watchlist(user_id: int) -> list[str]:
    with _connect() as conn:
        row = conn.execute("SELECT tickers FROM watchlists WHERE user_id = ?", (user_id,)).fetchone()
    if not row or not row[0]:
        return []
    return [x.strip().upper() for x in row[0].split(",") if x.strip()]


def save_watchlist(user_id: int, tickers: list[str]) -> None:
    clean = []
    for ticker in tickers:
        ticker = ticker.strip().upper()
        if ticker and ticker not in clean:
            clean.append(ticker)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO watchlists(user_id, tickers) VALUES(?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET tickers=excluded.tickers",
            (user_id, ",".join(clean)),
        )


def get_portfolio(user_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, ticker, market, shares, avg_cost, created_at, updated_at "
            "FROM portfolio_holdings WHERE user_id = ? ORDER BY ticker, id",
            (user_id,),
        ).fetchall()
    return [
        {
            "id": r[0], "ticker": r[1], "market": r[2],
            "shares": float(r[3]), "avg_cost": float(r[4]),
            "created_at": r[5], "updated_at": r[6],
        }
        for r in rows
    ]


def add_portfolio_holding(user_id: int, ticker: str, market: str, invested_amount: float, purchase_price: float) -> tuple[bool, str]:
    ticker = ticker.strip().upper()
    market = market.strip().upper()
    try:
        invested_amount = float(invested_amount)
        purchase_price = float(purchase_price)
    except (TypeError, ValueError):
        return False, "투자금액과 매수 가격을 숫자로 입력하세요."
    if not ticker:
        return False, "종목명 또는 종목코드를 입력하세요."
    if market not in {"US", "KR"}:
        return False, "시장을 US 또는 KR로 선택하세요."
    if invested_amount <= 0 or purchase_price <= 0:
        return False, "투자금액과 매수 가격은 0보다 커야 합니다."
    shares = invested_amount / purchase_price
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id, shares, avg_cost FROM portfolio_holdings "
            "WHERE user_id=? AND ticker=? AND market=? ORDER BY id LIMIT 1",
            (user_id, ticker, market),
        ).fetchone()
        if existing:
            holding_id, old_shares, old_avg = existing
            total_shares = float(old_shares) + shares
            weighted_avg = ((float(old_shares) * float(old_avg)) + invested_amount) / total_shares
            conn.execute(
                "UPDATE portfolio_holdings SET shares=?, avg_cost=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (total_shares, weighted_avg, holding_id),
            )
            conn.execute(
                "DELETE FROM portfolio_holdings WHERE user_id=? AND ticker=? AND market=? AND id<>?",
                (user_id, ticker, market, holding_id),
            )
            return True, f"기존 {ticker} 보유분에 합쳤습니다. 평균 매수가가 {weighted_avg:,.4f}로 계산되었습니다."
        conn.execute(
            "INSERT INTO portfolio_holdings(user_id, ticker, market, shares, avg_cost) VALUES(?,?,?,?,?)",
            (user_id, ticker, market, shares, purchase_price),
        )
    return True, f"{ticker}: {shares:,.6f}주를 추가했습니다. (투자금액 ÷ 매수 가격)"

def update_portfolio_holding(user_id: int, holding_id: int, ticker: str, market: str, invested_amount: float, purchase_price: float) -> tuple[bool, str]:
    ticker = ticker.strip().upper()
    market = market.strip().upper()
    try:
        invested_amount = float(invested_amount)
        purchase_price = float(purchase_price)
    except (TypeError, ValueError):
        return False, "투자금액과 매수 가격을 숫자로 입력하세요."
    if not ticker or market not in {"US", "KR"} or invested_amount <= 0 or purchase_price <= 0:
        return False, "종목/시장/투자금액/매수 가격을 확인하세요."
    shares = invested_amount / purchase_price
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE portfolio_holdings SET ticker=?, market=?, shares=?, avg_cost=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND user_id=?",
            (ticker, market, shares, purchase_price, holding_id, user_id),
        )
    return (cur.rowcount > 0, "포트폴리오를 수정했습니다." if cur.rowcount else "해당 보유종목을 찾지 못했습니다.")

def delete_portfolio_holding(user_id: int, holding_id: int) -> tuple[bool, str]:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM portfolio_holdings WHERE id=? AND user_id=?", (holding_id, user_id))
    return (cur.rowcount > 0, "포트폴리오에서 삭제했습니다." if cur.rowcount else "해당 보유종목을 찾지 못했습니다.")
