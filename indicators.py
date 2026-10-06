# indicators.py
import pandas as pd
import numpy as np


def add_rsi(df, period=14):
    """Relative Strength Index"""
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def add_atr(df, period=14):
    """Average True Range (volatility measure)"""
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(period).mean()
    return df


def add_sma(df, periods=[10, 20, 50, 200]):
    """Simple Moving Averages"""
    for p in periods:
        df[f'SMA_{p}'] = df['Close'].rolling(p).mean()
    return df


def add_ema(df, periods=[9, 21]):
    """Exponential Moving Averages"""
    for p in periods:
        df[f'EMA_{p}'] = df['Close'].ewm(span=p, adjust=False).mean()
    return df


def add_volume_avg(df, period=20):
    """Average Volume"""
    df['Vol_Avg'] = df['Volume'].rolling(period).mean()
    return df


def add_momentum_score(df):
    """Multi-timeframe momentum returns"""
    df['Ret_1M'] = df['Close'].pct_change(21)   # ~1 month
    df['Ret_3M'] = df['Close'].pct_change(63)   # ~3 months
    df['Ret_6M'] = df['Close'].pct_change(126)  # ~6 months
    df['Ret_1Y'] = df['Close'].pct_change(252)  # ~1 year
    return df


def add_macd(df, fast=12, slow=26, signal=9):
    """MACD indicator"""
    ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
    df['MACD'] = ema_fast - ema_slow
    df['MACD_Signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    return df


def add_bollinger_bands(df, period=20, std_dev=2):
    """Bollinger Bands"""
    df['BB_Middle'] = df['Close'].rolling(period).mean()
    bb_std = df['Close'].rolling(period).std()
    df['BB_Upper'] = df['BB_Middle'] + (std_dev * bb_std)
    df['BB_Lower'] = df['BB_Middle'] - (std_dev * bb_std)
    return df


def add_all_indicators(df):
    """एक ही call में सभी indicators add करें"""
    df = add_rsi(df)
    df = add_atr(df)
    df = add_sma(df)
    df = add_volume_avg(df)
    df = add_momentum_score(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    return df
