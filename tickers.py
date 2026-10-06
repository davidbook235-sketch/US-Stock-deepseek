# tickers.py
import streamlit as st
import pandas as pd
import requests
import io


@st.cache_data(ttl=86400, show_spinner=False)
def get_nasdaq_tickers(limit=250):
    """Nasdaq Trader FTP से listed tickers fetch करता है"""
    url = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    
    df = pd.read_csv(io.StringIO(resp.text), sep="|")
    
    # Test issues और footer row हटाएं
    df = df[df['Test Issue'] == 'N']
    df = df[df['Symbol'] != 'File Creation Time']
    
    tickers = df['Symbol'].dropna().unique().tolist()
    return tickers[:limit]


@st.cache_data(ttl=86400, show_spinner=False)
def get_sp500_tickers():
    """Wikipedia से S&P 500 tickers fetch करता है (User-Agent fix + Fallback)"""
    # --- Try 1: Wikipedia ---
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        tables = pd.read_html(io.StringIO(response.text))
        df = tables[0]
        tickers = df['Symbol'].tolist()
        tickers = [t.replace('.', '-') for t in tickers]
        
        if tickers:
            return tickers
    except Exception:
        pass  # Wikipedia fail हुआ तो fallback try करें

    # --- Try 2: GitHub CSV Fallback ---
    try:
        fallback_url = (
            "https://raw.githubusercontent.com/fja05680/sp500/"
            "master/S%26P%20500%20Historical%20Components%20%26%20Changes.csv"
        )
        df = pd.read_csv(fallback_url)
        tickers = df.iloc[:, 1].dropna().unique().tolist()
        tickers = [str(t).replace('.', '-') for t in tickers if str(t).strip()]
        return tickers
    except Exception:
        return []


def get_tickers(index_name, limit=None):
    """Index नाम के हिसाब से tickers return करता है"""
    if index_name == "Nasdaq 250":
        tickers = get_nasdaq_tickers(limit=250)
    elif index_name == "S&P 500":
        tickers = get_sp500_tickers()
    elif index_name == "Nasdaq 100":
        tickers = get_nasdaq_tickers(limit=100)
    else:
        tickers = []
    
    if limit:
        tickers = tickers[:limit]
    return tickers
