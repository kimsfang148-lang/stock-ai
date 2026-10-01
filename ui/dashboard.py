from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

from data.market_data import get_price_data
from scanner.market_scanner import scan_with_diagnostics
from analysis.csv_ai_ranker import compare_top50
from analysis.event_analyzer import analyze_news_events, analyze_disclosure_events
from data.news_data import get_news
from data.sec_data import get_submissions
from indicators.technical import add_indicators
from analysis.returns import period_returns, risk_metrics
from analysis.financial import basic_fundamental_scores
from analysis.score import score_horizons
from analysis.valuation import reference_fair_value
from analysis.scenarios import scenarios
from analysis.risk import risk_flags
from analysis.competitors import get_peers
from analysis.portfolio import position_size
from backtest.engine import run_backtest
from backtest.performance import summarize
from scanner.daily_candidates import daily_candidates
from scanner.ranking import rank_candidates
from scanner.daily_report import build_daily_report
from backtest.walk_forward import walk_forward
from ui.chart import price_chart
from ai.analyst import analyze, test_connection
from config.settings import AI_PROVIDER, OLLAMA_MODEL, OPENAI_MODEL
from config.currency import currency_for_market, format_money
from ui.account import render_account_sidebar, render_portfolio_page
from data.connection_status import get_connection_status
from data.ticker_resolver import resolve_ticker, infer_market
from data.dart_mapper import resolve_korean_corp_code
from data.dart_data import get_financials, get_key_indicators, get_disclosures
from alerts.webhook import send_webhook


def _init_state() -> None:
    defaults = {
        "analysis_bundle": None,
        "analysis_ai": None,
        "scanner_rows": None,
        "report_df": None,
        "report_path": None,
        "diagnostics": {},
        "news_ai": None,
        "disclosure_ai": None,
        "scanner_raw_rows": None,
        "scanner_diag": {},
        "scanner_min_long_used": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _safe_ticker(ticker: str, market: str) -> str:
    ticker = ticker.strip().upper()
    if market == "KR" and ticker.isdigit() and len(ticker) == 6:
        return ticker + ".KS"
    return ticker


def _analysis_market(ticker: str) -> str:
    return infer_market(ticker)


def _build_analysis(ticker: str, market: str, period: str, interval: str = "1d") -> dict | None:
    yf_ticker = _safe_ticker(ticker, market)
    df = get_price_data(yf_ticker, period=period, interval=interval)
    if df.empty:
        return None
    df = add_indicators(df)
    row = df.iloc[-1]
    try:
        info = yf.Ticker(yf_ticker).info
    except Exception:
        info = {}

    fundamentals = basic_fundamental_scores(info)
    scores = score_horizons(row.to_dict(), fundamentals)
    returns = period_returns(df)
    risks = risk_metrics(df)
    fair = reference_fair_value(float(row["Close"]), info.get("trailingPE"), info.get("priceToBook"))
    scen = scenarios(fair)
    flags = risk_flags(row.to_dict(), risks)
    return {
        "ticker": yf_ticker,
        "market": market,
        "period": period,
        "interval": interval,
        "df": df,
        "row": row,
        "info": info,
        "fundamentals": fundamentals,
        "scores": scores,
        "returns": returns,
        "risks": risks,
        "fair": fair,
        "scen": scen,
        "flags": flags,
    }


def _render_analysis(bundle: dict, ai_provider: str) -> None:
    ticker = bundle["ticker"]
    market = bundle["market"]
    df = bundle["df"]
    row = bundle["row"]
    scores = bundle["scores"]
    returns = bundle["returns"]
    risks = bundle["risks"]
    fair = bundle["fair"]
    scen = bundle["scen"]
    flags = bundle["flags"]
    currency_code, currency_symbol = currency_for_market(market)

    st.success(f"분석 완료: {ticker} · 통화 {currency_symbol} {currency_code}")
    tabs = st.tabs(["📊 대시보드", "📈 차트", "💰 수익률/위험", "🧪 백테스트", "📑 공시", "📰 뉴스", "🏭 경쟁사", "🎯 포지션", "🤖 AI"])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재가", format_money(row["Close"], market))
        c2.metric("RSI", f"{row['RSI']:.1f}")
        c3.metric("단기 참고점수", f"{scores['short']:.1f}/100")
        c4.metric("장기 참고점수", f"{scores['long']:.1f}/100")
        st.subheader("투자기간별 참고점수")
        st.dataframe(pd.DataFrame([scores], index=["점수"]).T.rename(columns={0: "참고점수"}), use_container_width=True)
        st.subheader("모델 참고 가격")
        price_table = pd.DataFrame([
            {"항목": "현재가", "가격": format_money(row["Close"], market)},
            {"항목": "모델 적정가치", "가격": format_money(fair, market)},
            {"항목": "관심가격", "가격": format_money(fair * 0.90 if fair else None, market)},
            {"항목": "리스크가격", "가격": format_money(fair * 0.72 if fair else None, market)},
        ])
        st.dataframe(price_table, hide_index=True, use_container_width=True)
        scenario_table = pd.DataFrame([
            {"시나리오": "Bear", "참고가격": format_money(scen.get("bear"), market)},
            {"시나리오": "Base", "참고가격": format_money(scen.get("base"), market)},
            {"시나리오": "Bull", "참고가격": format_money(scen.get("bull"), market)},
        ])
        st.dataframe(scenario_table, hide_index=True, use_container_width=True)
        if flags:
            st.warning(" / ".join(flags))

    with tabs[1]:
        st.caption(f"차트 간격: {bundle.get('interval', '1d')} · 데이터 기간: {bundle.get('period', '5y')}")
        st.plotly_chart(price_chart(df.tail(500), ticker), use_container_width=True)

    with tabs[2]:
        st.subheader("과거 수익률")
        st.dataframe(pd.DataFrame([returns]).T.rename(columns={0: "수익률"}).style.format("{:.2%}"), use_container_width=True)
        st.subheader("위험 지표")
        st.dataframe(pd.DataFrame([risks]).T.rename(columns={0: "값"}), use_container_width=True)

    with tabs[3]:
        st.subheader("전략 백테스트")
        initial = st.number_input(f"초기자금 ({currency_code})", min_value=1000, max_value=1_000_000_000, value=10_000, step=1000, key="backtest_initial")
        backtest_df = df.dropna()
        if backtest_df.empty or "Close" not in backtest_df.columns:
            st.info("백테스트에 사용할 유효한 가격 데이터가 없습니다. 다른 기간이나 시간 간격을 선택해 주세요.")
            result = {"final_value": float(initial), "return": 0.0, "trades": [], "equity": pd.DataFrame()}
        else:
            result = run_backtest(backtest_df, initial_cash=initial)
        summary = summarize(result, initial)
        summary_display = dict(summary)
        summary_display["Initial Value"] = format_money(initial, market)
        summary_display["Final Value"] = format_money(summary.get("Final Value"), market)
        for key in ["Total Return", "CAGR", "Max Drawdown", "Win Rate"]:
            if key in summary_display and summary_display[key] is not None:
                try:
                    summary_display[key] = f"{float(summary_display[key]):.2%}"
                except Exception:
                    pass
        st.dataframe(pd.DataFrame([summary_display]).T.rename(columns={0: "결과"}), use_container_width=True)
        if not result["equity"].empty:
            st.line_chart(result["equity"]["equity"])
        st.subheader("Walk-forward / Out-of-sample")
        wf = walk_forward(backtest_df, initial_cash=initial) if not backtest_df.empty else []
        if wf:
            st.dataframe(pd.DataFrame(wf), use_container_width=True)
        else:
            st.info("테스트 구간을 만들 만큼 충분한 과거 데이터가 필요합니다.")
        st.caption("백테스트는 미래 성과를 보장하지 않습니다.")

    with tabs[4]:
        if market == "US":
            try:
                sec = get_submissions(ticker)
                st.write(f"CIK: {sec.get('cik')}")
                if sec.get("filings"):
                    filing_df = pd.DataFrame(sec["filings"])
                    st.dataframe(filing_df[["filingDate", "form", "primaryDocument", "url"]], use_container_width=True)
                    if st.button("🤖 최신 SEC 공시 AI 분석", key="ai_sec_events"):
                        with st.spinner("공시 이벤트를 분석하는 중..."):
                            st.session_state["disclosure_ai"] = analyze_disclosure_events(ticker, sec["filings"], provider=ai_provider)
                    if st.session_state.get("disclosure_ai"):
                        st.markdown(st.session_state["disclosure_ai"])
                else:
                    st.info("SEC 제출자료를 찾지 못했습니다.")
            except Exception as e:
                st.error(f"SEC 조회 오류: {e}")
        else:
            try:
                corp_code = resolve_korean_corp_code(ticker)
                if not corp_code:
                    st.warning("DART에서 종목코드를 찾지 못했습니다. 6자리 KRX 종목코드를 입력하세요. 예: 005930")
                else:
                    st.write(f"DART corp_code: {corp_code}")
                    year = datetime.now().year - 1
                    fin = get_financials(corp_code, year)
                    if fin.get("rows"):
                        st.subheader(f"DART 재무제표 ({year})")
                        st.dataframe(pd.DataFrame(fin["rows"]), use_container_width=True)
                    ind = get_key_indicators(corp_code, year)
                    if ind.get("rows"):
                        st.subheader(f"DART 주요 재무지표 ({year})")
                        st.dataframe(pd.DataFrame(ind["rows"]), use_container_width=True)
                    disc = get_disclosures(corp_code=corp_code, page_count=20)
                    if disc.get("rows"):
                        st.subheader("최근 DART 공시")
                        disc_df = pd.DataFrame(disc["rows"])
                        st.dataframe(disc_df, use_container_width=True)
                        if st.button("🤖 최신 DART 공시 AI 분석", key="ai_dart_events"):
                            with st.spinner("공시 이벤트를 분석하는 중..."):
                                st.session_state["disclosure_ai"] = analyze_disclosure_events(ticker, disc["rows"], provider=ai_provider)
                        if st.session_state.get("disclosure_ai"):
                            st.markdown(st.session_state["disclosure_ai"])
            except Exception as e:
                st.error(f"DART 연결 오류: {e}")

    with tabs[5]:
        news = get_news(ticker)
        if not news:
            st.info("뉴스를 가져오지 못했습니다.")
        else:
            st.caption("최신 뉴스가 조회될 때 핵심 내용과 주가 영향 가능성을 로컬 AI로 분석할 수 있습니다.")
            if st.button("🤖 최신 뉴스 AI 분석", key="ai_news_events"):
                with st.spinner("뉴스 이벤트를 분석하는 중..."):
                    st.session_state["news_ai"] = analyze_news_events(ticker, news, provider=ai_provider)
            if st.session_state.get("news_ai"):
                st.markdown(st.session_state["news_ai"])
            for n in news:
                st.markdown(f"**{n['title']}**  \n{n['published']}  \n{n['url']}")

    with tabs[6]:
        peers = get_peers(ticker)
        if peers:
            st.dataframe(pd.DataFrame(peers), use_container_width=True)
        else:
            st.info("현재 기본 경쟁사 목록이 없습니다.")

    with tabs[7]:
        st.subheader("위험 기준 포지션 계산")
        st.caption("계산상 소수점 주식수까지 표시합니다. 실제 주문 가능 수량은 사용하는 증권사·상품의 거래 규칙을 따릅니다.")
        capital = st.number_input(f"투자 가능 자금 ({currency_code})", min_value=1000, value=1_000_000 if market == "KR" else 10_000, step=1000, key="position_capital")
        stop_pct = st.slider("손절폭 (%)", 1.0, 30.0, 10.0, 0.5, key="position_stop_pct")
        risk_pct = st.slider("계좌 위험 한도 (%)", 0.1, 5.0, 1.0, 0.1, key="position_risk_pct")
        st.info(f"계좌 위험 한도 {risk_pct:.1f}% = 손절이 실행된다고 가정할 때 감수할 최대 손실액 {format_money(capital * risk_pct / 100, market)}")
        entry = float(row["Close"])
        stop = entry * (1 - stop_pct / 100)
        sizing = position_size(capital, entry, stop, risk_pct / 100)
        st.dataframe(pd.DataFrame([
            {"항목": "진입가격", "값": format_money(entry, market)},
            {"항목": "손절가격", "값": format_money(stop, market)},
            {"항목": "위험금액", "값": format_money(sizing["risk_amount"], market)},
            {"항목": "계산 주식수 (소수점)", "값": f"{sizing['shares']:,.4f}주"},
            {"항목": "계산 주식수 (정수)", "값": f"{sizing['whole_shares']:,}주"},
            {"항목": "예상 포지션 가치 (소수점 기준)", "값": format_money(sizing["position_value"], market)},
        ]), hide_index=True, use_container_width=True)

    with tabs[8]:
        payload = {
            "ticker": ticker,
            "current_price": float(row["Close"]),
            "scores": scores,
            "returns": returns,
            "risk_metrics": risks,
            "rsi": float(row["RSI"]),
            "macd_bull": bool(row["MACD"] > row["MACD_SIGNAL"]),
            "fair_value": fair,
            "scenarios": scen,
            "risk_flags": flags,
            "fundamentals": bundle["fundamentals"],
        }
        if st.button("AI 종합분석 생성", key="ai_generate"):
            with st.spinner("AI 분석 중..."):
                st.session_state["analysis_ai"] = analyze(payload, provider=ai_provider)
        if st.session_state.get("analysis_ai"):
            st.markdown(st.session_state["analysis_ai"])
        else:
            st.info("Ollama(내 PC), 무료 규칙 기반 분석(웹에서 API 비용 0원), 또는 본인 Gemini API 중 하나를 선택하세요.")


def _render_diagnostics(ticker: str, market: str, ai_provider: str) -> None:
    with st.expander("🧰 연결 진단 — 일반 분석에는 필수 아님", expanded=False):
        st.caption("데이터 서버나 AI가 연결되는지만 확인하는 도구입니다. 문제가 없다면 누르지 않아도 됩니다.")
        c1, c2, c3, c4 = st.columns(4)
        diagnostics = st.session_state["diagnostics"]
        with c1:
            if st.button("한국 DART 연결 확인", key="diag_dart"):
                if market != "KR":
                    diagnostics["DART"] = "한국 시장을 선택한 뒤 확인하세요."
                else:
                    code = resolve_korean_corp_code(ticker)
                    diagnostics["DART"] = f"정상: corp_code={code}" if code else "연결은 되었지만 종목코드를 찾지 못했습니다. DART_API_KEY를 확인하세요."
        with c2:
            if st.button("미국 SEC 연결 확인", key="diag_sec"):
                if market != "US":
                    diagnostics["SEC"] = "미국 시장을 선택한 뒤 확인하세요."
                else:
                    try:
                        sec = get_submissions(ticker, limit=1)
                        diagnostics["SEC"] = f"정상: CIK {sec.get('cik')}"
                    except Exception as e:
                        diagnostics["SEC"] = f"오류: {e}"
        with c3:
            if st.button("선택한 AI 연결 확인", key="diag_ai"):
                ok, message = test_connection(provider=ai_provider)
                diagnostics["AI"] = ("정상: " if ok else "오류: ") + str(message)
        with c4:
            if st.button("Webhook 연결 확인", key="diag_webhook"):
                diagnostics["Webhook"] = str(send_webhook("Stock AI Pro 연결 테스트"))
        for name, message in diagnostics.items():
            st.info(f"**{name}:** {message}")


def _render_scanner() -> None:
    st.divider()
    st.subheader("🔎 오늘의 시장 스캐너")
    st.caption("현재 기본 예시 유니버스를 대상으로 합니다. 전체 시장 스캔은 종목 마스터/데이터 공급원이 추가로 필요합니다.")
    scan_market = st.selectbox("스캔 시장", ["US", "KR"], key="scan_market")
    min_long = st.slider("최소 장기 참고점수", 0, 100, 60, key="scan_min_long")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("시장 스캔 실행", key="market_scan_run"):
            with st.spinner("시장 스캔 중... 시간이 걸릴 수 있습니다."):
                from scanner.daily_candidates import DEFAULT_US, DEFAULT_KR
                universe = DEFAULT_US if scan_market == "US" else DEFAULT_KR
                raw_rows, diag = scan_with_diagnostics(universe, period="2y")
                st.session_state["scanner_raw_rows"] = raw_rows
                st.session_state["scanner_diag"] = diag
                st.session_state["scanner_rows"] = rank_candidates(raw_rows, min_long=min_long)
                st.session_state["scanner_min_long_used"] = min_long
    with c2:
        if st.button("상위 50종목 CSV 생성", key="daily_report_run"):
            with st.spinner("리포트 생성 중..."):
                report_df, report_path = build_daily_report(scan_market, top_n=50)
                st.session_state["report_df"] = report_df
                st.session_state["report_path"] = report_path

    rows = st.session_state.get("scanner_rows")
    if rows is not None:
        diag = st.session_state.get("scanner_diag", {})
        used = st.session_state.get("scanner_min_long_used", min_long)
        if rows:
            scan_df = pd.DataFrame(rows)
            if "Price" in scan_df.columns:
                scan_df["Price"] = scan_df["Price"].map(lambda x: format_money(x, scan_market))
            st.success(f"{len(rows)}개 후보 발견 · 장기 참고점수 {used}점 이상")
            st.dataframe(scan_df, use_container_width=True)
        else:
            evaluated = int(diag.get("evaluated", 0) or 0)
            data_empty = int(diag.get("data_empty", 0) or 0)
            failed = int(diag.get("evaluation_failed", 0) or 0)
            errors = diag.get("errors", []) or []
            st.warning(f"조건을 만족하는 후보가 없습니다. 현재 설정: 장기 참고점수 {used}점 이상")
            st.markdown(f"**왜 없었나요?** 전체 {diag.get('total', 0)}종목 중 데이터 확인 가능 {evaluated}종목, 데이터 없음 {data_empty}종목, 지표 계산 실패 {failed}종목입니다.")
            if evaluated:
                raw_df = pd.DataFrame(st.session_state.get("scanner_raw_rows", []))
                if not raw_df.empty and "장기점수" in raw_df.columns:
                    max_score = float(raw_df["장기점수"].max())
                    below = int((raw_df["장기점수"] < used).sum())
                    st.info(f"데이터가 있는 {evaluated}종목 중 최고 장기점수는 {max_score:.1f}점이며, {below}종목이 기준 {used}점 미만이었습니다. 점수 기준을 낮추면 후보가 늘어날 수 있습니다.")
            if errors:
                with st.expander("데이터 오류 상세", expanded=False):
                    st.dataframe(pd.DataFrame(errors), use_container_width=True)

    report_df = st.session_state.get("report_df")
    report_path = st.session_state.get("report_path")
    if report_path is not None:
        st.success(f"{len(report_df)}개 후보를 저장했습니다: {report_path}")
        if report_df is not None and not report_df.empty:
            st.download_button(
                "CSV 다운로드",
                report_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=Path(report_path).name,
                mime="text/csv",
                key="daily_report_download",
            )
            st.divider()
            st.subheader("🤖 CSV 상위 50종목 AI 비교")
            st.caption("CSV에 포함된 최대 50개 종목을 한꺼번에 비교해 Top 10 / 관심 / 관찰 / 제외로 분류하고, 각 분류의 근거를 설명합니다.")
            if len(report_df) < 50:
                st.warning(f"현재 스캔 유니버스에서 확보된 종목은 {len(report_df)}개입니다. 50개 전체 비교를 하려면 스캔 종목 유니버스를 더 늘려야 합니다.")
            if st.button("🤖 상위 50종목 AI 비교 실행", key="ai_compare_top50"):
                with st.spinner("상위 종목 50개를 AI가 비교하는 중..."):
                    st.session_state["top50_ai"] = compare_top50(report_df.to_dict("records"), provider=st.session_state.get("ai_provider", "local"))
            if st.session_state.get("top50_ai"):
                st.markdown(st.session_state["top50_ai"])

def render_dashboard() -> None:
    _init_state()
    user = render_account_sidebar()

    with st.sidebar:
        st.subheader("🧭 메뉴")
        page_mode = st.radio("화면", ["📈 주식 분석", "💼 내 포트폴리오"], key="main_page_mode")

    if page_mode == "💼 내 포트폴리오":
        st.title("💼 내 포트폴리오")
        st.caption("종목별 보유 현황, 투자금, 평균 매수가, 평가금액과 수익률을 관리합니다.")
        render_portfolio_page(user)
        return

    st.title("📈 Stock AI Pro")
    st.caption("기술적 분석 + 실적/재무 + DART/SEC + 뉴스 + 백테스트 + 시장 스캐너 + 로컬 AI")
    if user:
        st.caption(f"현재 로그인: {user['display_name']} (@{user['username']})")

    with st.expander("🔌 외부 데이터/API 연결 상태", expanded=False):
        status = get_connection_status()
        rows = [{"연결": name, "상태": "연결됨" if info["enabled"] else "미연결", "설명": info["detail"]} for name, info in status.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with st.sidebar:
        st.subheader("🤖 AI 설정")
        ai_provider = st.selectbox(
            "AI 제공자",
            ["local", "free_rules", "gemini_user"],
            index={"local": 0, "free_rules": 1, "gemini_user": 2}.get(AI_PROVIDER, 0),
            format_func=lambda x: {
                "local": "무료 로컬 AI (Ollama)",
                "free_rules": "무료 규칙 기반 분석 (API 비용 0원)",
                "gemini_user": "사용자 본인 Gemini API (본인 한도 사용)",
            }[x],
            key="ai_provider",
        )
        if ai_provider == "local":
            st.caption(f"로컬 모델: {OLLAMA_MODEL} · 내 PC에서 실행할 때 사용")
        elif ai_provider == "free_rules":
            st.caption("외부 AI API를 호출하지 않습니다. 공용 웹에서 운영자 비용이 발생하지 않습니다.")
        else:
            st.session_state["user_gemini_api_key"] = st.text_input(
                "본인의 Gemini API 키",
                value=st.session_state.get("user_gemini_api_key", ""),
                type="password",
                placeholder="AIza...",
                help="운영자 키를 사용하지 않습니다. 입력한 키는 현재 Streamlit 세션에서만 사용하고 계정 DB나 GitHub에는 저장하지 않습니다.",
                key="user_gemini_key_input",
            ).strip()
            if st.button("🗑️ Gemini 키 지우기", key="clear_user_gemini_key"):
                st.session_state["user_gemini_api_key"] = ""
                st.session_state["user_gemini_key_input"] = ""
                st.rerun()
            st.caption("사용량/한도와 과금 여부는 입력한 키의 Google 프로젝트 설정에 적용됩니다.")
            st.warning("이 키는 AI 호출을 위해 앱 서버로 전달됩니다. 공용 서버 운영자가 키를 절대 볼 수 없는 구조가 필요하다면 브라우저 직접 호출 방식이 별도로 필요합니다.")
        ticker_input = st.text_input(
            "종목명 또는 종목코드",
            "005930" if st.session_state.get("analysis_bundle") and st.session_state["analysis_bundle"]["market"] == "KR" else "NVDA",
            placeholder="엔비디아 / NVDA / 삼성전자 / 005930",
            key="ticker_input",
        ).strip()
        market_default = 1 if _analysis_market(ticker_input) == "KR" else 0
        market = st.selectbox("시장", ["US", "KR"], index=market_default, key="analysis_market")
        currency_code, currency_symbol = currency_for_market(market)
        st.caption(f"통화: {currency_symbol} {currency_code} · 한글 종목명도 입력할 수 있습니다.")

        st.markdown("**차트 간격 — 숫자를 먼저 입력하고 단위를 선택하세요**")
        ic1, ic2 = st.columns([1, 1.25])
        with ic1:
            interval_value = st.number_input("간격 숫자", min_value=1, max_value=10000, value=1, step=1, key="analysis_interval_value")
        with ic2:
            interval_unit = st.selectbox(
                "시간 단위",
                ["초", "분", "시간", "일", "개월", "년"],
                index=1,
                key="analysis_interval_unit",
            )
        unit_map = {"초": "s", "분": "m", "시간": "h", "일": "d", "개월": "mo", "년": "y"}
        selected_interval = f"custom:{unit_map[interval_unit]}:{int(interval_value)}"

        st.markdown("**차트 데이터 기간 — 숫자를 먼저 입력하고 단위를 선택하세요**")
        pc1, pc2 = st.columns([1, 1.25])
        with pc1:
            period_value = st.number_input(
                "기간 숫자", min_value=1, max_value=10000, value=3, step=1,
                key="analysis_period_value",
            )
        with pc2:
            period_unit = st.selectbox(
                "기간 단위", ["초", "분", "시간", "일", "개월", "년"],
                index=4, key="analysis_period_unit",
            )
        period_map = {"초": "s", "분": "m", "시간": "h", "일": "d", "개월": "mo", "년": "y"}
        period = f"custom:{period_map[period_unit]}:{int(period_value)}"
        if interval_unit == "초":
            st.caption("초 단위 차트는 무료 원천 데이터의 한계로 1분 데이터를 가장 가까운 기준으로 사용합니다.")
        if interval_unit in {"분", "시간"} or period_unit in {"초", "분", "시간"}:
            st.caption("분/시간/초 단위 과거 데이터는 데이터 제공처의 보관 기간 제한이 적용될 수 있습니다.")
        else:
            st.caption("요청한 기간을 기준으로 데이터를 가져옵니다. 개월/년 기간은 일봉 데이터를 기반으로 계산합니다.")
        run = st.button("분석 실행", type="primary", key="analysis_run")

    if run:
        resolved_ticker, resolved_name, resolve_reason = resolve_ticker(ticker_input, market)
        if not resolved_ticker:
            st.session_state["analysis_bundle"] = None
            st.error(resolve_reason)
        else:
            with st.spinner(f"{resolved_ticker} 분석 중..."):
                bundle = _build_analysis(resolved_ticker, market, period, interval=selected_interval)
            if bundle is None:
                st.session_state["analysis_bundle"] = None
                st.error(f"{resolved_name or ticker_input} → {resolved_ticker}로 인식했지만 가격 데이터를 가져오지 못했습니다.")
            else:
                st.session_state["analysis_bundle"] = bundle
                st.session_state["analysis_ai"] = None
                st.session_state["news_ai"] = None
                st.session_state["disclosure_ai"] = None
                st.success(f"종목 인식: {resolved_name or ticker_input} → **{resolved_ticker}** · {resolve_reason}")

    bundle = st.session_state.get("analysis_bundle")
    if bundle:
        if ticker_input and _safe_ticker(ticker_input, market) != bundle["ticker"]:
            st.warning(f"현재 입력은 {ticker_input}이지만 화면에는 마지막으로 분석한 {bundle['ticker']} 결과가 표시됩니다. 새 종목은 '분석 실행'을 눌러주세요.")
        _render_analysis(bundle, ai_provider)
    else:
        st.info("왼쪽에서 종목과 시장을 선택한 뒤 '분석 실행'을 눌러주세요.")

    with st.expander("🔔 뉴스·공시 이벤트 감시", expanded=False):
        st.caption("새 뉴스/공시를 확인한 뒤, 새 항목이 있으면 로컬 AI로 핵심 내용과 주가 영향 가능성을 분석할 수 있습니다. 자동 분석은 Ollama를 사용하므로 OpenAI 비용이 발생하지 않습니다.")
        auto_event = st.checkbox("분석 실행 때 최신 이벤트도 함께 확인", value=False, key="auto_event_check")
        if auto_event and bundle:
            if st.button("🔄 최신 뉴스·공시 확인 및 AI 분석", key="event_refresh_analyze"):
                event_messages = []
                with st.spinner("최신 뉴스·공시를 확인하고 분석하는 중..."):
                    latest_news = get_news(bundle["ticker"], limit=10)
                    if latest_news:
                        st.session_state["news_ai"] = analyze_news_events(bundle["ticker"], latest_news, provider=ai_provider)
                        event_messages.append(f"뉴스 {len(latest_news)}건 분석")
                    if bundle["market"] == "KR":
                        corp_code = resolve_korean_corp_code(bundle["ticker"])
                        if corp_code:
                            disc = get_disclosures(corp_code=corp_code, page_count=10)
                            if disc.get("rows"):
                                st.session_state["disclosure_ai"] = analyze_disclosure_events(bundle["ticker"], disc["rows"], provider=ai_provider)
                                event_messages.append(f"DART 공시 {len(disc['rows'])}건 분석")
                    else:
                        sec = get_submissions(bundle["ticker"], limit=10)
                        if sec.get("filings"):
                            st.session_state["disclosure_ai"] = analyze_disclosure_events(bundle["ticker"], sec["filings"], provider=ai_provider)
                            event_messages.append(f"SEC 공시 {len(sec['filings'])}건 분석")
                st.success(" / ".join(event_messages) if event_messages else "새로 분석할 뉴스·공시를 찾지 못했습니다.")
        if st.session_state.get("news_ai"):
            st.subheader("📰 뉴스 이벤트 AI 분석")
            st.markdown(st.session_state["news_ai"])
        if st.session_state.get("disclosure_ai"):
            st.subheader("📑 공시 이벤트 AI 분석")
            st.markdown(st.session_state["disclosure_ai"])

    _render_diagnostics(_safe_ticker(ticker_input, market), market, ai_provider)
    _render_scanner()
