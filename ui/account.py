import pandas as pd
import streamlit as st

from data.auth import (
    add_portfolio_holding,
    authenticate,
    create_account,
    delete_portfolio_holding,
    get_portfolio,
    get_watchlist,
    save_watchlist,
    update_portfolio_holding,
)
from analysis.portfolio_tracker import build_portfolio_rows, portfolio_summary
from config.currency import format_money
from data.migration import _migrate_result
from data.ticker_resolver import resolve_ticker


def _return_style(value):
    if pd.isna(value):
        return "color: black"
    value = float(value)
    if value > 0:
        return "color: green; font-weight: 700"
    if value < 0:
        return "color: red; font-weight: 700"
    return "color: black; font-weight: 700"


def _render_portfolio_editor(user: dict) -> None:
    st.markdown("### ➕ 포트폴리오 추가")
    st.caption("종목명/코드 + 실제 투자금액 + 매수 가격을 입력하면 보유 주식 수를 자동 계산합니다.")
    holdings = get_portfolio(user["id"])

    with st.form("portfolio_add_form"):
        c1, c2 = st.columns(2)
        with c1:
            ticker_input = st.text_input("종목명 또는 종목코드", placeholder="엔비디아 / NVDA / 삼성전자 / 005930")
            market = st.selectbox("시장", ["KR", "US"], format_func=lambda x: "한국 (KRW)" if x == "KR" else "미국 (USD)")
        with c2:
            invested_amount = st.number_input(
                "투자한 금액",
                min_value=0.01,
                value=1_000_000.0 if market == "KR" else 1_000.0,
                step=1000.0 if market == "KR" else 100.0,
            )
            purchase_price = st.number_input(
                "매수 가격 (1주 기준)",
                min_value=0.0001,
                value=10000.0 if market == "KR" else 100.0,
                step=1.0,
            )
        submitted = st.form_submit_button("포트폴리오에 추가", type="primary")

    if submitted:
        resolved, display_name, reason = resolve_ticker(ticker_input, market)
        if not resolved:
            st.error(reason)
        else:
            ok, msg = add_portfolio_holding(user["id"], resolved, market, invested_amount, purchase_price)
            if ok:
                shares = invested_amount / purchase_price
                st.success(f"{display_name or ticker_input} → {resolved} · {shares:,.6f}주 · {msg}")
                st.rerun()
            else:
                st.error(msg)

    if not holdings:
        st.info("아직 등록된 포트폴리오가 없습니다.")
        return

    rows = build_portfolio_rows(holdings)
    summary = portfolio_summary(rows)
    k1, k2 = st.columns(2)
    k1.metric("🇰🇷 KRW 투자금", format_money(summary["KRW"]["invested"], "KR"))
    k2.metric("🇰🇷 KRW 평가손익", format_money(summary["KRW"]["pnl"], "KR"), f"{summary['KRW']['return_pct']:.2%}" if summary['KRW']['return_pct'] is not None else None)
    u1, u2 = st.columns(2)
    u1.metric("🇺🇸 USD 투자금", format_money(summary["USD"]["invested"], "US"))
    u2.metric("🇺🇸 USD 평가손익", format_money(summary["USD"]["pnl"], "US"), f"{summary['USD']['return_pct']:.2%}" if summary['USD']['return_pct'] is not None else None)

    display = []
    for r in rows:
        display.append({
            "종목": r["ticker"],
            "시장": r["market"],
            "보유수량": f"{r['shares']:,.6f}주",
            "평균매수가": format_money(r["avg_cost"], r["market"]),
            "현재가": format_money(r["current_price"], r["market"]) if r["current_price"] is not None else "조회 실패",
            "투자금": format_money(r["invested"], r["market"]),
            "평가금액": format_money(r["current_value"], r["market"]) if r["current_value"] is not None else "-",
            "평가손익": format_money(r["pnl"], r["market"]) if r["pnl"] is not None else "-",
            "수익률": r["return_pct"] if r["return_pct"] is not None else 0.0,
        })
    display_df = pd.DataFrame(display)
    styled = display_df.style.map(_return_style, subset=["수익률"]).format({"수익률": "{:.2%}"})
    st.dataframe(styled, hide_index=True, use_container_width=True)
    st.caption("수익률 색상: 양수=초록색 · 음수=빨간색 · 0%=검정색. 같은 종목을 추가하면 기존 보유분과 합쳐지고 가중평균 매수가가 다시 계산됩니다.")

    st.markdown("### ✏️ 포트폴리오 수정/삭제")
    for h in holdings:
        with st.expander(f"{h['ticker']} ({h['market']}) · 현재 {h['shares']:,.6f}주", expanded=False):
            current_invested = float(h["shares"]) * float(h["avg_cost"])
            with st.form(f"portfolio_edit_{h['id']}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    e_ticker = st.text_input("종목명/코드", h["ticker"], key=f"pt_{h['id']}")
                with c2:
                    e_invested = st.number_input("투자금액", min_value=0.01, value=current_invested, step=1000.0 if h["market"] == "KR" else 100.0, key=f"pi_{h['id']}")
                with c3:
                    e_cost = st.number_input("매수 가격 (1주)", min_value=0.0001, value=float(h["avg_cost"]), step=1.0, key=f"pc_{h['id']}")
                b1, b2 = st.columns(2)
                with b1:
                    save = st.form_submit_button("수정 저장")
                with b2:
                    delete = st.form_submit_button("삭제")
                if save:
                    resolved, _, reason = resolve_ticker(e_ticker, h["market"])
                    if not resolved:
                        st.error(reason)
                    else:
                        ok, msg = update_portfolio_holding(user["id"], h["id"], resolved, h["market"], e_invested, e_cost)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()
                if delete:
                    ok, msg = delete_portfolio_holding(user["id"], h["id"])
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()


def render_account_sidebar() -> dict | None:
    """Render local account controls and return the logged-in user, if any."""
    user = st.session_state.get("user")
    with st.sidebar:
        if _migrate_result[0]:
            st.success("기존 계좌/포트폴리오 데이터를 자동으로 가져왔습니다.")
        st.divider()
        st.subheader("👤 계정")
        if user:
            st.success(f"로그인: {user['display_name']} (@{user['username']})")
            watchlist = get_watchlist(user["id"])
            watch_text = st.text_input(
                "관심종목",
                ", ".join(watchlist),
                help="예: AAPL, NVDA, 005930.KS",
                key="account_watchlist",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("관심종목 저장", key="save_watchlist"):
                    save_watchlist(user["id"], [x for x in watch_text.replace(" ", "").split(",") if x])
                    st.success("저장했습니다.")
            with c2:
                if st.button("로그아웃", key="logout"):
                    st.session_state.pop("user", None)
                    st.rerun()
            return user

        mode = st.radio("계정", ["게스트", "로그인", "회원가입"], horizontal=True, key="account_mode")
        if mode == "게스트":
            st.caption("계정 없이도 주식 분석을 사용할 수 있습니다.")
            return None
        if mode == "로그인":
            with st.form("login_form"):
                username = st.text_input("아이디")
                password = st.text_input("비밀번호", type="password")
                submitted = st.form_submit_button("로그인", type="primary")
            if submitted:
                found = authenticate(username, password)
                if found:
                    st.session_state["user"] = found
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 맞지 않습니다.")
        else:
            with st.form("register_form"):
                username = st.text_input("아이디", help="영문/숫자/._- 3~30자")
                display_name = st.text_input("표시 이름")
                password = st.text_input("비밀번호", type="password")
                password2 = st.text_input("비밀번호 확인", type="password")
                submitted = st.form_submit_button("계정 만들기", type="primary")
            if submitted:
                if password != password2:
                    st.error("비밀번호 확인이 일치하지 않습니다.")
                else:
                    ok, message = create_account(username, password, display_name)
                    (st.success if ok else st.error)(message)
        return st.session_state.get("user")


def render_portfolio_page(user: dict | None) -> None:
    st.subheader("💼 내 포트폴리오")
    if not user:
        st.info("포트폴리오를 저장하려면 왼쪽에서 회원가입 또는 로그인을 해주세요.")
        return
    _render_portfolio_editor(user)
