#!/usr/bin/env python3
"""
Technical Analysis Chart Generator
Generates professional charts for Gold, Oil, and EUR/USD
"""

import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return sma, upper, lower

def compute_fibonacci(high, low):
    diff = high - low
    levels = {
        '0.0% (High)': high,
        '23.6%': high - 0.236 * diff,
        '38.2%': high - 0.382 * diff,
        '50.0%': high - 0.500 * diff,
        '61.8%': high - 0.618 * diff,
        '78.6%': high - 0.786 * diff,
        '100.0% (Low)': low,
    }
    return levels

# ── Chart 1: Beginner-friendly overview chart ────────────────────────────

def chart_beginner(df, title, support, resistance, filename):
    """Simple candlestick with support/resistance zones and moving averages."""
    fig, ax = plt.subplots(figsize=(14, 7))

    # Candlesticks manually
    up = df[df.Close >= df.Open]
    down = df[df.Close < df.Open]

    ax.bar(up.index, up.Close - up.Open, bottom=up.Open, width=0.6, color='#26a69a', alpha=0.9)
    ax.bar(up.index, up.High - up.Close, bottom=up.Close, width=0.15, color='#26a69a')
    ax.bar(up.index, up.Low - up.Open, bottom=up.Open, width=0.15, color='#26a69a')

    ax.bar(down.index, down.Close - down.Open, bottom=down.Open, width=0.6, color='#ef5350', alpha=0.9)
    ax.bar(down.index, down.High - down.Open, bottom=down.Open, width=0.15, color='#ef5350')
    ax.bar(down.index, down.Low - down.Close, bottom=down.Close, width=0.15, color='#ef5350')

    # Moving averages
    sma20 = df.Close.rolling(20).mean()
    sma50 = df.Close.rolling(50).mean()
    ax.plot(df.index, sma20, color='#2196F3', linewidth=1.5, label='SMA 20', alpha=0.8)
    ax.plot(df.index, sma50, color='#FF9800', linewidth=1.5, label='SMA 50', alpha=0.8)

    # Support & resistance zones
    ax.axhspan(support * 0.995, support * 1.005, color='green', alpha=0.15, label=f'Support ~{support:,.0f}')
    ax.axhspan(resistance * 0.995, resistance * 1.005, color='red', alpha=0.15, label=f'Resistance ~{resistance:,.0f}')
    ax.axhline(y=support, color='green', linestyle='--', linewidth=1, alpha=0.6)
    ax.axhline(y=resistance, color='red', linestyle='--', linewidth=1, alpha=0.6)

    # Annotations
    ax.annotate('SUPPORT', xy=(df.index[-10], support), fontsize=9, color='green', fontweight='bold',
                ha='center', va='top')
    ax.annotate('RESISTANCE', xy=(df.index[-10], resistance), fontsize=9, color='red', fontweight='bold',
                ha='center', va='bottom')

    ax.set_title(f'{title} — Beginner Overview', fontsize=16, fontweight='bold', pad=15)
    ax.set_ylabel('Price', fontsize=12)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved {filename}")

# ── Chart 2: Intermediate with RSI + MACD panels ────────────────────────

def chart_intermediate(df, title, support, resistance, filename):
    """Candlestick + Bollinger Bands + RSI + MACD (3 panels)."""
    rsi = compute_rsi(df.Close)
    macd_line, signal_line, macd_hist = compute_macd(df.Close)
    bb_mid, bb_upper, bb_lower = compute_bollinger(df.Close)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12),
                                         gridspec_kw={'height_ratios': [3, 1, 1]},
                                         sharex=True)

    # Panel 1: Price + Bollinger Bands
    up = df[df.Close >= df.Open]
    down = df[df.Close < df.Open]

    ax1.bar(up.index, up.Close - up.Open, bottom=up.Open, width=0.6, color='#26a69a', alpha=0.9)
    ax1.bar(up.index, up.High - up.Close, bottom=up.Close, width=0.15, color='#26a69a')
    ax1.bar(up.index, up.Low - up.Open, bottom=up.Open, width=0.15, color='#26a69a')
    ax1.bar(down.index, down.Close - down.Open, bottom=down.Open, width=0.6, color='#ef5350', alpha=0.9)
    ax1.bar(down.index, down.High - down.Open, bottom=down.Open, width=0.15, color='#ef5350')
    ax1.bar(down.index, down.Low - down.Close, bottom=down.Close, width=0.15, color='#ef5350')

    ax1.plot(df.index, bb_upper, color='#9C27B0', linewidth=1, alpha=0.6, label='BB Upper')
    ax1.plot(df.index, bb_mid, color='#9C27B0', linewidth=1, linestyle='--', alpha=0.4, label='BB Mid')
    ax1.plot(df.index, bb_lower, color='#9C27B0', linewidth=1, alpha=0.6, label='BB Lower')
    ax1.fill_between(df.index, bb_upper, bb_lower, color='#9C27B0', alpha=0.05)

    ax1.axhline(y=support, color='green', linestyle='--', linewidth=1, alpha=0.6)
    ax1.axhline(y=resistance, color='red', linestyle='--', linewidth=1, alpha=0.6)

    sma50 = df.Close.rolling(50).mean()
    sma200 = df.Close.rolling(200).mean()
    ax1.plot(df.index, sma50, color='#FF9800', linewidth=1.2, label='SMA 50', alpha=0.7)
    if sma200.notna().sum() > 0:
        ax1.plot(df.index, sma200, color='#F44336', linewidth=1.2, label='SMA 200', alpha=0.7)

    ax1.set_title(f'{title} — Intermediate Technical Analysis', fontsize=16, fontweight='bold', pad=15)
    ax1.set_ylabel('Price', fontsize=11)
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.2)

    # Panel 2: RSI
    ax2.plot(df.index, rsi, color='#2196F3', linewidth=1.2)
    ax2.axhline(y=70, color='red', linestyle='--', linewidth=0.8, alpha=0.6)
    ax2.axhline(y=30, color='green', linestyle='--', linewidth=0.8, alpha=0.6)
    ax2.axhline(y=50, color='gray', linestyle=':', linewidth=0.5)
    ax2.fill_between(df.index, rsi, 70, where=(rsi >= 70), color='red', alpha=0.2)
    ax2.fill_between(df.index, rsi, 30, where=(rsi <= 30), color='green', alpha=0.2)
    ax2.set_ylabel('RSI (14)', fontsize=11)
    ax2.set_ylim(10, 90)
    ax2.grid(True, alpha=0.2)

    # Panel 3: MACD
    colors = ['#26a69a' if v >= 0 else '#ef5350' for v in macd_hist]
    ax3.bar(df.index, macd_hist, color=colors, width=0.6, alpha=0.7)
    ax3.plot(df.index, macd_line, color='#2196F3', linewidth=1.2, label='MACD')
    ax3.plot(df.index, signal_line, color='#FF9800', linewidth=1.2, label='Signal')
    ax3.axhline(y=0, color='gray', linewidth=0.5)
    ax3.set_ylabel('MACD', fontsize=11)
    ax3.legend(loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.2)

    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax3.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved {filename}")

# ── Chart 3: Expert with Fibonacci + Volume Profile ─────────────────────

def chart_expert(df, title, fib_high, fib_low, filename):
    """Candlestick + Fibonacci retracements + Volume + EMA ribbons."""
    fibs = compute_fibonacci(fib_high, fib_low)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10),
                                    gridspec_kw={'height_ratios': [3, 1]},
                                    sharex=True)

    # Price
    up = df[df.Close >= df.Open]
    down = df[df.Close < df.Open]
    ax1.bar(up.index, up.Close - up.Open, bottom=up.Open, width=0.6, color='#26a69a', alpha=0.9)
    ax1.bar(up.index, up.High - up.Close, bottom=up.Close, width=0.15, color='#26a69a')
    ax1.bar(up.index, up.Low - up.Open, bottom=up.Open, width=0.15, color='#26a69a')
    ax1.bar(down.index, down.Close - down.Open, bottom=down.Open, width=0.6, color='#ef5350', alpha=0.9)
    ax1.bar(down.index, down.High - down.Open, bottom=down.Open, width=0.15, color='#ef5350')
    ax1.bar(down.index, down.Low - down.Close, bottom=down.Close, width=0.15, color='#ef5350')

    # EMA ribbon
    for span, alpha in [(8, 0.3), (13, 0.35), (21, 0.4), (34, 0.45), (55, 0.5)]:
        ema = df.Close.ewm(span=span, adjust=False).mean()
        ax1.plot(df.index, ema, linewidth=0.8, alpha=alpha, color='#2196F3')
    ema200 = df.Close.ewm(span=200, adjust=False).mean()
    if ema200.notna().sum() > 0:
        ax1.plot(df.index, ema200, color='#F44336', linewidth=1.5, alpha=0.7, label='EMA 200')

    # Fibonacci levels
    fib_colors = ['#4CAF50', '#8BC34A', '#CDDC39', '#FFC107', '#FF9800', '#FF5722', '#F44336']
    for (label, level), color in zip(fibs.items(), fib_colors):
        ax1.axhline(y=level, color=color, linestyle='--', linewidth=0.8, alpha=0.7)
        ax1.text(df.index[-1], level, f'  {label}: {level:,.1f}', fontsize=8,
                 color=color, va='center', fontweight='bold')

    ax1.set_title(f'{title} — Expert: Fibonacci + EMA Ribbon + Volume', fontsize=16, fontweight='bold', pad=15)
    ax1.set_ylabel('Price', fontsize=11)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.15)

    # Volume
    vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df.Close, df.Open)]
    ax2.bar(df.index, df.Volume, color=vol_colors, width=0.6, alpha=0.7)
    vol_sma = df.Volume.rolling(20).mean()
    ax2.plot(df.index, vol_sma, color='#FF9800', linewidth=1.2, label='Vol SMA 20')
    ax2.set_ylabel('Volume', fontsize=11)
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.2)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved {filename}")

# ── Chart 4: Scenario / Decision Tree visual ────────────────────────────

def chart_scenario_dashboard(filename):
    """Visual scenario matrix for all 3 assets."""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.axis('off')

    scenarios = [
        ('Rapid De-escalation\n(15%)', 'Gold ↓ $3,800–4,100\nOil ↓ $70–80\nEUR/USD ↑ 1.17–1.19', '#4CAF50'),
        ('Gradual Normalization\n(35%)', 'Gold → $4,200–4,600\nOil ↓ $85–100\nEUR/USD → 1.14–1.16', '#2196F3'),
        ('Prolonged Disruption\n(35%)', 'Gold ↑ $5,000–5,500\nOil → $100–130\nEUR/USD ↓ 1.11–1.13', '#FF9800'),
        ('Major Escalation\n(15%)', 'Gold ↑↑ $6,000+\nOil ↑↑ $130–150+\nEUR/USD ↓↓ 1.08–1.10', '#F44336'),
    ]

    # Title
    ax.text(0.5, 0.95, 'SCENARIO ANALYSIS DASHBOARD — March 24, 2026',
            fontsize=20, fontweight='bold', ha='center', va='top',
            transform=ax.transAxes)
    ax.text(0.5, 0.90, 'Central Variable: Middle East Conflict / Strait of Hormuz Resolution Timeline',
            fontsize=13, ha='center', va='top', transform=ax.transAxes,
            style='italic', color='#666')

    # Boxes
    box_width = 0.20
    box_height = 0.35
    start_x = 0.05
    y_pos = 0.45

    for i, (title, body, color) in enumerate(scenarios):
        x = start_x + i * 0.24
        rect = plt.Rectangle((x, y_pos), box_width, box_height,
                              linewidth=2, edgecolor=color, facecolor=color,
                              alpha=0.1, transform=ax.transAxes)
        ax.add_patch(rect)
        # Header
        ax.text(x + box_width/2, y_pos + box_height - 0.03, title,
                fontsize=12, fontweight='bold', ha='center', va='top',
                transform=ax.transAxes, color=color)
        # Body
        ax.text(x + box_width/2, y_pos + box_height/2 - 0.03, body,
                fontsize=11, ha='center', va='center',
                transform=ax.transAxes, family='monospace')

    # Key insight box
    insight_y = 0.12
    rect2 = plt.Rectangle((0.05, insight_y - 0.02), 0.90, 0.22,
                           linewidth=1.5, edgecolor='#333', facecolor='#f5f5f5',
                           transform=ax.transAxes)
    ax.add_patch(rect2)
    ax.text(0.5, insight_y + 0.17, 'KEY CROSS-ASSET INSIGHTS', fontsize=13,
            fontweight='bold', ha='center', va='top', transform=ax.transAxes)
    insights = (
        '● Gold: Most asymmetric — bullish in 3/4 scenarios. Best risk/reward.\n'
        '● Oil: Most binary — $75 or $150 on one variable. Size positions carefully.\n'
        '● EUR/USD: Clearest directional — bearish in 3/4 scenarios. Highest conviction short.'
    )
    ax.text(0.5, insight_y + 0.11, insights, fontsize=11, ha='center', va='top',
            transform=ax.transAxes, family='monospace', linespacing=1.5)

    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=150, bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    print(f"  ✓ Saved {filename}")

# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("Fetching market data...")

    # Fetch 1 year of data for each asset
    tickers = {
        'Gold': 'GC=F',
        'Oil (Brent)': 'BZ=F',
        'EUR/USD': 'EURUSD=X',
    }

    data = {}
    for name, ticker in tickers.items():
        print(f"  Downloading {name} ({ticker})...")
        df = yf.download(ticker, period='1y', interval='1d', progress=False)
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.DatetimeIndex(df.index)
        data[name] = df
        print(f"    Got {len(df)} rows, last date: {df.index[-1].strftime('%Y-%m-%d')}")

    # ── Gold charts ──────────────────────────────────────────────────────
    gold = data['Gold']
    gold_high = gold.High.max()
    gold_low = gold.Low.min()
    gold_last = float(gold.Close.iloc[-1])

    # Estimate support/resistance from data
    gold_support = round(gold_last * 0.95, -1)   # ~5% below
    gold_resistance = round(gold_last * 1.05, -1) # ~5% above

    print("\nGenerating Gold charts...")
    chart_beginner(gold, 'GOLD (XAU/USD)', gold_support, gold_resistance, 'gold_beginner.png')
    chart_intermediate(gold, 'GOLD (XAU/USD)', gold_support, gold_resistance, 'gold_intermediate.png')
    chart_expert(gold, 'GOLD (XAU/USD)', gold_high, gold_low, 'gold_expert.png')

    # ── Oil charts ───────────────────────────────────────────────────────
    oil = data['Oil (Brent)']
    oil_high = oil.High.max()
    oil_low = oil.Low.min()
    oil_last = float(oil.Close.iloc[-1])

    oil_support = round(oil_last * 0.93, 0)
    oil_resistance = round(oil_last * 1.06, 0)

    print("\nGenerating Oil charts...")
    chart_beginner(oil, 'OIL (Brent Crude)', oil_support, oil_resistance, 'oil_beginner.png')
    chart_intermediate(oil, 'OIL (Brent Crude)', oil_support, oil_resistance, 'oil_intermediate.png')
    chart_expert(oil, 'OIL (Brent Crude)', oil_high, oil_low, 'oil_expert.png')

    # ── EUR/USD charts ───────────────────────────────────────────────────
    eurusd = data['EUR/USD']
    eur_high = eurusd.High.max()
    eur_low = eurusd.Low.min()
    eur_last = float(eurusd.Close.iloc[-1])

    eur_support = round(eur_last - 0.03, 4)
    eur_resistance = round(eur_last + 0.03, 4)

    print("\nGenerating EUR/USD charts...")
    chart_beginner(eurusd, 'EUR/USD', eur_support, eur_resistance, 'eurusd_beginner.png')
    chart_intermediate(eurusd, 'EUR/USD', eur_support, eur_resistance, 'eurusd_intermediate.png')
    chart_expert(eurusd, 'EUR/USD', eur_high, eur_low, 'eurusd_expert.png')

    # ── Scenario dashboard ───────────────────────────────────────────────
    print("\nGenerating scenario dashboard...")
    chart_scenario_dashboard('scenario_dashboard.png')

    print(f"\n{'='*50}")
    print(f"All charts saved to: {CHARTS_DIR}/")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
