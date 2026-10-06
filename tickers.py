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
    """Wikipedia से S&P 500 tickers fetch करता है"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    tickers = df['Symbol'].tolist()
    # Yahoo Finance में '.' की जगह '-' use होता है (जैसे BRK.B -> BRK-B)
    tickers = [t.replace('.', '-') for t in tickers]
    return tickers


def get_tickers(index_name, limit=None):
    """Index नाम के हिसाब से tickers return करता है"""
    if index_name == "Nasdaq 250":
        tickers = get_nasdaq_tickers(limit=250)
    elif index_name == "S&P 500":
        tickers = get_sp500_tickers()
    elif index_name == "Nasdaq 100":
        all_nasdaq = get_nasdaq_tickers(limit=100)
        tickers = all_nasdaq
    else:
        tickers = []
    
    if limit:
        tickers = tickers[:limit]
    return tickers
