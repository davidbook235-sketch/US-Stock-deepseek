import yfinance as yf
import pandas as pd
import numpy as np
import time
import streamlit as st
from indicators import *
from tickers import get_tickers

@st.cache_data(ttl=3600, show_spinner=False)
def download_batch(tickers_chunk):
    """एक chunk के लिए data download करता है (1-hour cache)"""
    try:
        df = yf.download(
            list(tickers_chunk),
            period='1y',
            interval='1d',
            group_by='ticker',
            auto_adjust=True,
            progress=False,
            threads=True
        )
        return df
    except Exception as e:
        st.warning(f"Batch download failed: {e}")
        return None

def scan_stock_from_data(ticker, df):
    """एक ticker के data से signals निकालता है"""
    try:
        if df is None or len(df) < 200:
            return None

        t_df = pd.DataFrame({
            'Open': df['Open'], 'High': df['High'],
            'Low': df['Low'], 'Close': df['Close'], 'Volume': df['Volume']
        }).dropna()

        if len(t_df) < 200:
            return None

        t_df = add_rsi(t_df)
        t_df = add_atr(t_df)
        t_df = add_sma(t_df)
        t_df = add_volume_avg(t_df)
        t_df = add_momentum_score(t_df)

        latest = t_df.iloc[-1]
        signals = []

        if 30 < latest['RSI'] < 50 and t_df['RSI'].iloc[-2] < 30:
            signals.append("RSI Recovery")
        if (latest['Close'] > latest['SMA_10'] and
            latest['Close'] > latest['SMA_20'] and
            latest['Close'] > latest['SMA_50']):
            signals.append("Trend Alignment")
        if latest['Volume'] > 1.5 * latest['Vol_Avg']:
            signals.append("Volume Surge")
        if (latest['Ret_1M'] > 0 and latest['Ret_3M'] > 0 and
            latest['Ret_6M'] > 0):
            signals.append("Consistent Momentum")

        score = len(signals) * 25

        return {
            'Ticker': ticker,
            'Price': round(float(latest['Close']), 2),
            'RSI': round(float(latest['RSI']), 1),
            'ATR': round(float(latest['ATR']), 2),
            'Score': score,
            'Ret_1M': round(float(latest['Ret_1M']) * 100, 1),
            'Ret_3M': round(float(latest['Ret_3M']) * 100, 1),
            'Vol_Ratio': round(float(latest['Volume'] / latest['Vol_Avg']), 2),
            'Signals': ", ".join(signals) if signals else "None",
        }
    except Exception:
        return None

def scan_index(index_name, min_score=25, progress_bar=None):
    """किसी भी index को chunks में scan करता है"""
    tickers = get_tickers(index_name)
    if not tickers:
        return pd.DataFrame()

    all_results = []
    chunk_size = 50
    chunks = [tickers[i:i+chunk_size] for i in range(0, len(tickers), chunk_size)]

    for idx, chunk in enumerate(chunks):
        if progress_bar:
            progress_bar.progress(
                (idx + 1) / len(chunks),
                text=f"Chunk {idx+1}/{len(chunks)} — {len(chunk)} stocks..."
            )

        batch_data = download_batch(tuple(chunk))

        if batch_data is None:
            continue

        for ticker in chunk:
            try:
                if ticker in batch_data.columns.get_level_values(0):
                    ticker_df = batch_data[ticker]
                    result = scan_stock_from_data(ticker, ticker_df)
                    if result and result['Score'] >= min_score:
                        all_results.append(result)
            except Exception:
                continue

        if idx < len(chunks) - 1:
            time.sleep(2)

    if not all_results:
        return pd.DataFrame()

    return pd.DataFrame(all_results).sort_values('Score', ascending=False)
