# backtest.py
import yfinance as yf
import pandas as pd
import numpy as np
from indicators import add_rsi, add_atr, add_sma, add_macd


def run_backtest(ticker, start='2022-01-01', end='2025-01-01',
                 rsi_buy=35, rsi_sell=65, atr_mult=2.0,
                 initial_capital=10000, use_trend_filter=True):
    """
    RSI + Trend + ATR stop-loss based backtest.
    
    Entry: RSI < rsi_buy AND price > SMA_200 (if trend filter on)
    Exit:  RSI > rsi_sell OR price < stop_loss (ATR-based)
    """
    try:
        df = yf.download(ticker, start=start, end=end,
                         interval='1d', auto_adjust=True, progress=False)
        if df.empty or len(df) < 200:
            return None

        # Multi-index columns flatten (yfinance sometimes returns these)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = add_rsi(df)
        df = add_atr(df)
        df = add_sma(df, [50, 200])
        df = add_macd(df)
        df = df.dropna()

        if len(df) < 30:
            return None

        position = False
        entry_price = 0
        stop_loss = 0
        cash = initial_capital
        trades = []
        equity_curve = [initial_capital]
        equity_dates = [df.index[0]]

        for i in range(1, len(df)):
            price = float(df['Close'].iloc[i])
            rsi = float(df['RSI'].iloc[i])
            date = df.index[i]

            if not position:
                # Entry condition
                trend_ok = (price > float(df['SMA_200'].iloc[i])) if use_trend_filter else True
                if rsi < rsi_buy and trend_ok:
                    position = True
                    entry_price = price
                    stop_loss = price - (atr_mult * float(df['ATR'].iloc[i]))
                    trades.append({
                        'type': 'BUY',
                        'date': date,
                        'price': round(price, 2),
                        'rsi': round(rsi, 1)
                    })
            else:
                # Exit condition
                if rsi > rsi_sell or price < stop_loss:
                    pnl_pct = (price - entry_price) / entry_price * 100
                    cash *= (1 + pnl_pct / 100)
                    trades.append({
                        'type': 'SELL',
                        'date': date,
                        'price': round(price, 2),
                        'rsi': round(rsi, 1),
                        'pnl_pct': round(pnl_pct, 2),
                        'reason': 'RSI Exit' if rsi > rsi_sell else 'Stop Loss'
                    })
                    position = False

            equity_curve.append(cash)
            equity_dates.append(date)

        trades_df = pd.DataFrame(trades)
        sell_trades = trades_df[trades_df['type'] == 'SELL'] if not trades_df.empty else pd.DataFrame()

        if sell_trades.empty:
            return {
                'ticker': ticker,
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'trades': trades_df,
                'equity_curve': pd.Series(equity_curve, index=equity_dates)
            }

        wins = sell_trades[sell_trades['pnl_pct'] > 0]
        losses = sell_trades[sell_trades['pnl_pct'] <= 0]

        total = len(sell_trades)
        win_rate = len(wins) / total * 100

        equity_series = pd.Series(equity_curve, index=equity_dates)
        total_return = (equity_curve[-1] - initial_capital) / initial_capital * 100

        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        max_dd = drawdown.min() * 100

        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe = 0

        # Profit factor = total gains / total losses
        gross_profit = wins['pnl_pct'].sum() if not wins.empty else 0
        gross_loss = abs(losses['pnl_pct'].sum()) if not losses.empty else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

        return {
            'ticker': ticker,
            'total_trades': total,
            'win_rate': round(win_rate, 1),
            'total_return': round(total_return, 2),
            'max_drawdown': round(max_dd, 2),
            'sharpe': round(sharpe, 2),
            'avg_win': round(wins['pnl_pct'].mean(), 2) if not wins.empty else 0,
            'avg_loss': round(losses['pnl_pct'].mean(), 2) if not losses.empty else 0,
            'profit_factor': round(profit_factor, 2),
            'trades': trades_df,
            'equity_curve': equity_series
        }

    except Exception as e:
        print(f"Backtest error for {ticker}: {e}")
        return None


def backtest_multiple(tickers, **kwargs):
    """Multiple tickers पर एक साथ backtest"""
    results = []
    for t in tickers:
        r = run_backtest(t, **kwargs)
        if r:
            results.append({
                'Ticker': t,
                'Trades': r['total_trades'],
                'Win Rate %': r['win_rate'],
                'Return %': r['total_return'],
                'Max DD %': r['max_drawdown'],
                'Sharpe': r['sharpe'],
                'Profit Factor': r['profit_factor']
            })
    return pd.DataFrame(results).sort_values('Return %', ascending=False) if results else pd.DataFrame()
