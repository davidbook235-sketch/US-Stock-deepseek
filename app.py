# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scanner import scan_index
from backtest import run_backtest

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="US Swing Trade Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------- MOBILE-FRIENDLY CSS ----------
st.markdown("""
<style>
@media (max-width: 600px) {
    .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
        width: 100% !important;
    }
    .stDataFrame { font-size: 0.8rem !important; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }
    .stTabs [data-baseweb="tab"] { font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📈 US Swing Trade Scanner")

# ---------- TABS ----------
tab1, tab2, tab3 = st.tabs(["🔍 Scanner", "📊 Backtest", "📖 Guide"])


# ============================================================
# TAB 1: SCANNER
# ============================================================
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

    if st.button("🚀 Run Scan", use_container_width=True, key="scan_btn"):
        progress = st.progress(0, text="Starting...")
        with st.spinner(f"Scanning {index_choice}..."):
            results = scan_index(index_choice, min_score=min_score,
                                 progress_bar=progress)
            progress.empty()
            st.session_state['scan_results'] = results
            st.session_state['scan_index'] = index_choice

    # ---------- FILTERS + RESULTS ----------
    if 'scan_results' in st.session_state:
        results = st.session_state['scan_results']

        if results.empty:
            st.warning("कोई signal नहीं मिला. Min Score कम करके try करें.")
        else:
            st.success(
                f"✅ {len(results)} stocks found in "
                f"{st.session_state['scan_index']}"
            )

            # ---------- FILTER PANEL ----------
            with st.expander("🎛️ Filters & Sorting", expanded=False):
                fcol1, fcol2 = st.columns(2)

                with fcol1:
                    # Unique signals
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

                    rsi_min = int(results['RSI'].min())
                    rsi_max = int(results['RSI'].max())
                    rsi_range = st.slider(
                        "RSI Range",
                        min_value=0, max_value=100,
                        value=(max(0, rsi_min), min(100, rsi_max))
                    )

                with fcol2:
                    ret_min = int(results['Ret_1M'].min())
                    ret_max = int(results['Ret_1M'].max())
                    if ret_min == ret_max:
                        ret_max = ret_min + 1
                    ret_range = st.slider(
                        "1M Return % Range",
                        min_value=ret_min, max_value=ret_max,
                        value=(ret_min, ret_max)
                    )

                    sort_by = st.selectbox(
                        "Sort By",
                        ["Score", "Ret_1M", "Ret_3M", "RSI", "Vol_Ratio"],
                        index=0
                    )
                    sort_order = st.radio(
                        "Order",
                        ["Descending", "Ascending"],
                        horizontal=True
                    )

            # ---------- APPLY FILTERS ----------
            filtered = results.copy()

            if selected_signals:
                filtered = filtered[
                    filtered['Signals'].apply(
                        lambda x: any(s in x for s in selected_signals)
                    )
                ]

            filtered = filtered[
                (filtered['RSI'] >= rsi_range[0]) &
                (filtered['RSI'] <= rsi_range[1])
            ]

            filtered = filtered[
                (filtered['Ret_1M'] >= ret_range[0]) &
                (filtered['Ret_1M'] <= ret_range[1])
            ]

            filtered = filtered.sort_values(
                sort_by, ascending=(sort_order == "Ascending")
            )

            # ---------- DISPLAY ----------
            st.caption(f"Showing {len(filtered)} of {len(results)} stocks")

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
                    "Ret_1M": st.column_config.NumberColumn(
                        "Ret 1M", format="%.1f%%"
                    ),
                    "Ret_3M": st.column_config.NumberColumn(
                        "Ret 3M", format="%.1f%%"
                    ),
                    "RSI": st.column_config.NumberColumn(format="%.1f"),
                    "ATR": st.column_config.NumberColumn(format="$%.2f"),
                    "Vol_Ratio": st.column_config.NumberColumn(
                        "Vol Ratio", format="%.2fx"
                    ),
                }
            )

            # ---------- EXPORT ----------
            csv = filtered.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                f"{st.session_state['scan_index'].replace(' ', '_')}_scan.csv",
                "text/csv",
                use_container_width=True
            )


# ============================================================
# TAB 2: BACKTEST
# ============================================================
with tab2:
    st.subheader("Strategy Backtest")
    st.caption("Entry: RSI < Buy AND Price > SMA_200 (optional) | "
               "Exit: RSI > Sell OR ATR Stop-Loss")

    bt_mode = st.radio(
        "Mode",
        ["Single Stock", "Multiple Stocks"],
        horizontal=True
    )

    if bt_mode == "Single Stock":
        bt_ticker = st.text_input("Ticker", value="AAPL").upper().strip()
    else:
        bt_tickers_input = st.text_input(
            "Tickers (comma separated)",
            value="AAPL,MSFT,NVDA,AMZN,GOOGL"
        )

    col1, col2 = st.columns(2)
    with col1:
        rsi_buy = st.slider("RSI Buy", 20, 50, 35, key="bt_rsi_buy")
        atr_mult = st.slider("ATR Multiplier", 1.0, 4.0, 2.0, 0.5,
                             key="bt_atr")
    with col2:
        rsi_sell = st.slider("RSI Sell", 50, 80, 65, key="bt_rsi_sell")
        use_trend = st.checkbox("Use 200-SMA Trend Filter", value=True,
                                key="bt_trend")

    if st.button("📊 Run Backtest", use_container_width=True,
                 key="bt_btn"):
        with st.spinner("Backtesting..."):
            # ---------- SINGLE STOCK ----------
            if bt_mode == "Single Stock":
                if not bt_ticker:
                    st.error("Ticker डालें.")
                else:
                    result = run_backtest(
                        bt_ticker,
                        rsi_buy=rsi_buy,
                        rsi_sell=rsi_sell,
                        atr_mult=atr_mult,
                        use_trend_filter=use_trend
                    )

                    if result and result['total_trades'] > 0:
                        # Metrics row 1
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Trades", result['total_trades'])
                        m2.metric("Win Rate", f"{result['win_rate']}%")
                        m3.metric("Total Return",
                                  f"{result['total_return']}%")

                        # Metrics row 2
                        m4, m5, m6 = st.columns(3)
                        m4.metric("Max Drawdown",
                                  f"{result['max_drawdown']}%")
                        m5.metric("Sharpe Ratio", result['sharpe'])
                        m6.metric("Profit Factor", result['profit_factor'])

                        # Avg win / loss
                        m7, m8 = st.columns(2)
                        m7.metric("Avg Win", f"{result['avg_win']}%")
                        m8.metric("Avg Loss", f"{result['avg_loss']}%")

                        # ---------- EQUITY CURVE ----------
                        eq = result['equity_curve']
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=eq.index,
                            y=eq.values,
                            mode='lines',
                            name='Equity',
                            line=dict(color='#00CC96', width=2),
                            fill='tozeroy',
                            fillcolor='rgba(0, 204, 150, 0.1)'
                        ))
                        fig.update_layout(
                            title="Equity Curve",
                            height=320,
                            margin=dict(l=10, r=10, t=40, b=10),
                            showlegend=False,
                            xaxis_title="",
                            yaxis_title="Portfolio Value ($)"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # ---------- TRADE HISTORY ----------
                        with st.expander("📜 Trade History"):
                            st.dataframe(
                                result['trades'],
                                use_container_width=True,
                                hide_index=True
                            )

                        # ---------- DOWNLOAD TRADES ----------
                        trades_csv = result['trades'].to_csv(index=False)
                        st.download_button(
                            "📥 Download Trades CSV",
                            trades_csv,
                            f"{bt_ticker}_trades.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    else:
                        st.error(
                            "No trades generated. Parameters बदल कर try करें."
                        )

            # ---------- MULTIPLE STOCKS ----------
            else:
                tickers = [
                    t.strip().upper()
                    for t in bt_tickers_input.split(",")
                    if t.strip()
                ]

                if not tickers:
                    st.error("कम से कम एक ticker डालें.")
                else:
                    results_list = []
                    progress = st.progress(0, text="Backtesting...")

                    for i, t in enumerate(tickers):
                        progress.progress(
                            (i + 1) / len(tickers),
                            text=f"Backtesting {t} ({i+1}/{len(tickers)})..."
                        )
                        r = run_backtest(
                            t,
                            rsi_buy=rsi_buy,
                            rsi_sell=rsi_sell,
                            atr_mult=atr_mult,
                            use_trend_filter=use_trend
                        )
                        if r and r['total_trades'] > 0:
                            results_list.append({
                                'Ticker': t,
                                'Trades': r['total_trades'],
                                'Win Rate %': r['win_rate'],
                                'Return %': r['total_return'],
                                'Max DD %': r['max_drawdown'],
                                'Sharpe': r['sharpe'],
                                'Profit Factor': r['profit_factor']
                            })
                    progress.empty()

                    if results_list:
                        df_results = pd.DataFrame(results_list).sort_values(
                            'Return %', ascending=False
                        )
                        st.success(f"✅ {len(df_results)} stocks backtested")

                        st.dataframe(
                            df_results,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Return %": st.column_config.NumberColumn(
                                    format="%.2f%%"
                                ),
                                "Win Rate %": st.column_config.NumberColumn(
                                    format="%.1f%%"
                                ),
                                "Max DD %": st.column_config.NumberColumn(
                                    format="%.2f%%"
                                ),
                            }
                        )

                        # Aggregate stats
                        st.markdown("**📊 Portfolio Averages**")
                        avg_cols = st.columns(3)
                        avg_cols[0].metric(
                            "Avg Return",
                            f"{df_results['Return %'].mean():.2f}%"
                        )
                        avg_cols[1].metric(
                            "Avg Win Rate",
                            f"{df_results['Win Rate %'].mean():.1f}%"
                        )
                        avg_cols[2].metric(
                            "Avg Sharpe",
                            f"{df_results['Sharpe'].mean():.2f}"
                        )

                        # Download
                        csv = df_results.to_csv(index=False)
                        st.download_button(
                            "📥 Download Results CSV",
                            csv,
                            "backtest_results.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning(
                            "किसी भी ticker में trades generate नहीं हुए."
                        )


# ============================================================
# TAB 3: GUIDE
# ============================================================
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

    ---

    ### 📊 Backtest कैसे पढ़ें

    | Metric | अच्छा Value | मतलब |
    |---|---|---|
    | **Win Rate** | > 50% | कितने trades profit में बंद हुए |
    | **Profit Factor** | > 1.5 | Total profit / Total loss |
    | **Sharpe Ratio** | > 1.0 | Risk-adjusted return |
    | **Max Drawdown** | < 20% | सबसे बड़ा loss from peak |
    | **Avg Win/Loss** | > 1.5 | Winning trades की average size |

    ---

    ### ⚠️ ज़रूरी Warnings

    1. **Backtest = past performance** — future guarantee नहीं
    2. **Overfitting से बचें** — एक stock पर parameters optimize न करें
    3. **Paper trade करें पहले** — Real money से पहले test करें
    4. **ATR stop-loss हमेशा use करें** — Risk management सबसे ज़रूरी
    5. **Position sizing** — 1 trade में capital का 2% से ज्यादा न लगाएं

    ---

    ### 🚀 Deployment

    1. सभी files GitHub पर push करें
    2. [share.streamlit.io](https://share.streamlit.io) पर deploy करें
    3. Main file: `app.py`
    4. Mobile पर automatic responsive होगा
    """)
