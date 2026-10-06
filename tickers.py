# tickers.py
import streamlit as st          # <--- यह line missing थी!
import pandas as pd
import requests
import io


@st.cache_data(ttl=86400, show_spinner=False)
def get_nasdaq_tickers(limit=250):
    """Nasdaq Trader FTP से listed tickers fetch करता है"""
    url = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
    resp = requests.get(url, timeout=10)
    df = pd.read_csv(io.StringIO(resp.text), sep="|")
    
    # Test issues और footer row हटाएं
    df = df[df['Test Issue'] == 'N']
    df = df[df['Symbol'] != 'File Creation Time']
    
    tickers = df['Symbol'].dropna().unique().tolist()
    return tickers[:limit]


@st.cache_data(ttl=86400, show_spinner=False)
def get_sp500_tickers():
    """Wikipedia से S&P 500 tickers fetch करता है (User-Agent fix)"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text))
        df = tables[0]
        tickers = df['Symbol'].tolist()
        # Yahoo Finance में '.' की जगह '-' use होता है (जैसे BRK.B -> BRK-B)
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        st.warning(f"S&P 500 list fetch failed: {e}")
        return []
