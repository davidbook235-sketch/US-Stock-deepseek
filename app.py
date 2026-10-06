import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scanner import scan_index
from backtest import run_backtest

st.set_page_config(page_title="Swing Scanner", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@media (max-width: 600px) {
    .stButton > button { min-height: 48px !important;
        font-size: 1rem !important; width: 100% !important; }
    .stDataFrame { font-size: 0.8rem !important; }
    h1 { font-size: 1.4rem !important; }
    .stTabs [data-baseweb="tab"] { font-size: 0.85rem !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📈 US Swing Trade Scanner")

tab1, tab2, tab3 = st.tabs(["🔍 Scanner", "📊 Backtest", "📖 Guide"])

# ---------- TAB 1: SCANNER ----------
with tab1:
    st.subheader("Index Scanner")

    col1, col2 = st.columns(2)
    with col1:
        index_choice = st.selectbox(
            "Select Index",
            ["Nasdaq 250", "Nasdaq 100", "S&P 500"]
        )
    with col2:
        min_score = st.slider("Min Score", 0, 100, 25, 25)

    if st.button("🚀 Run Scan", use_container_width=True):
        progress = st.progress(0, text="Starting...")
        with st.spinner(f"Scanning {index_choice}..."):
            results = scan_index(index_choice, min_score=min_score,
                                 progress_bar=progress)
            progress.empty()

            # Session state में save करें ताकि filtering के बाद भी रहे
            st.session_state['scan_results'] = results
            st.session_state['scan_index'] = index_choice

    # ---------- FILTERS + RESULTS ----------
    if 'scan_results' in st.session_state:
        results = st.session_state['scan_results']

        if results.empty:
            st.warning("कोई signal नहीं मिला. Min Score कम करके try करें.")
        else:
            st.success(f"✅ {len(results)} stocks found in "
                       f"{st.session_state['scan_index']}")

            # ---------- FILTER PANEL ----------
            with st.expander("🎛️ Filters & Sorting", expanded=False):
                fcol1, fcol2 = st.columns(2)

                with fcol1:
                    # Signal filter
                    all_signals = set()
                    for s in results['Signals']:
                        for sig in s.split(", "):
                            if sig != "None":
                                all_signals.add(sig)

                    selected_signals = st.multiselect(
                        "Filter by Signal",
                        options=sorted(all_signals),
                        default=[]
                    )

                    rsi_range = st.slider("RSI Range", 0, 100, (0, 100))

                with fcol2:
                    ret_range = st.slider(
                        "1M Return % Range",
                        int(results['Ret_1M'].min()),
                        int(results['Ret_1M'].max()),
                        (int(results['Ret_1M'].min()),
                         int(results['Ret_1M'].max()))
                    )

                    sort_by = st.selectbox(
                        "Sort By",
                        ["Score", "Ret_1M", "Ret_3M", "RSI", "Vol_Ratio"],
                        index=0
                    )
                    sort_order = st.radio(
                        "Order", ["Descending", "Ascending"],
                        horizontal=True
                    )

            # ---------- APPLY FILTERS ----------
            filtered = results.copy()

            # Signal filter
            if selected_signals:
                filtered = filtered[
                    filtered['Signals'].apply(
                        lambda x: any(s in x for s in selected_signals)
                    )
                ]

            # RSI filter
            filtered = filtered[
                (filtered['RSI'] >= rsi_range[0]) &
                (filtered['RSI'] <= rsi_range[1])
            ]

            # Return filter
            filtered = filtered[
                (filtered['Ret_1M'] >= ret_range[0]) &
                (filtered['Ret_1M'] <= ret_range[1])
            ]

            # Sorting
            filtered = filtered.sort_values(
                sort_by, ascending=(sort_order == "Ascending")
            )

            # ---------- DISPLAY ----------
            st.caption(f"Showing {len(filtered)} of {len(results)} stocks")

            # Mobile-friendly display with score coloring
            st.dataframe(
                filtered,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Score",
                        min_value=0, max_value=100, format="%d"
                    ),
                    "Price": st.column_config.NumberColumn(format="$%.2f"),
                    "Ret_1M": st.column_config.NumberColumn(format="%.1f%%"),
                    "Ret_3M": st.column_config.NumberColumn(format="%.1f%%"),
                    "RSI": st.column_config.NumberColumn(format="%.1f"),
                    "Vol_Ratio": st.column_config.NumberColumn(
                        "Vol Ratio", format="%.2fx"
                    ),
                }
            )

            # ---------- EXPORT ----------
            csv = filtered.to_csv(index=False)
            st.download_button(
                "📥 Download CSV", csv,
                f"{st.session_state['scan_index'].replace(' ', '_')}_scan.csv",
                "text/csv", use_container_width=True
            )

# ---------- TAB 2: BACKTEST ----------
with tab2:
    st.subheader("Strategy Backtest")
    bt_ticker = st.text_input("Ticker", value="AAPL")
    col1, col2 = st.columns(2)
    with col1:
        rsi_buy = st.slider("RSI Buy", 20, 50, 35)
        atr_mult = st.slider("ATR Multiplier", 1.0, 4.0, 2.0, 0.5)
    with col2:
        rsi_sell = st.slider("RSI Sell", 50, 80, 65)

    if st.button("📊 Run Backtest", use_container_width=True):
        with st.spinner("Backtesting..."):
            result = run_backtest(bt_ticker, rsi_buy=rsi_buy,
                                  rsi_sell=rsi_sell, atr_mult=atr_mult)
            if result and result['total_trades'] > 0:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Trades", result['total_trades'])
                m2.metric("Win Rate", f"{result['win_rate']}%")
                m3.metric("Return", f"{result['total_return']}%")
                m4.metric("Max DD", f"{result['max_drawdown']}%")
                st.metric("Sharpe Ratio", result['sharpe'])
            else:
                st.error("Backtest failed or no trades")

# ---------- TAB 3: GUIDE ----------
with tab3:
    st.markdown("""
    ### 📖 Scanner कैसे use करें

    **Score System (0-100):**
    - 25 = 1 signal, 50 = 2 signals, 75 = 3 signals, 100 = 4 signals
    - **75+ Score** = Strong setup (सबसे reliable)
    - **50 Score** = Moderate setup

    **Signals Explained:**
    - **RSI Recovery** — Oversold से उबर रहा है (mean reversion)
    - **Trend Alignment** — Price सभी SMAs के ऊपर (uptrend)
    - **Volume Surge** — Average से 1.5x ज्यादा volume (breakout confirm)
    - **Consistent Momentum** — 1M, 3M, 6M सभी positive

    **Filter Tips:**
    - RSI 40-60 range में swing entries best होती हैं
    - Vol_Ratio > 1.5 वाले stocks में breakout ज्यादा reliable
    - Ret_3M positive होना चाहिए (trend confirm)

    **⚠️ Warnings:**
    - Backtest = past performance, future guarantee नहीं
    - हमेशा ATR-based stop-loss use करें
    - Real money से पहले paper trade करें
    """)
