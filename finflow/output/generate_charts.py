#!/usr/bin/env python3
"""
FinFlow Professional Chart Generator — Multi-instrument support.
Bloomberg/TradingView-inspired dark theme charts.
Three audience levels: Beginner, Intermediate, Professional + Scenario Dashboard.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from matplotlib.patches import FancyBboxPatch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from finflow.instruments import InstrumentConfig, fmt_price, INSTRUMENTS
from finflow.data.market_data import fetch_ohlcv, compute_indicators

CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── Professional Dark Theme ──────────────────────────────────────────────

DARK = {
    'bg': '#0d1117', 'panel': '#161b22', 'grid': '#21262d', 'border': '#30363d',
    'text': '#e6edf3', 'text_dim': '#8b949e', 'text_muted': '#484f58',
    'green': '#7dcea0', 'green_dim': '#52be80', 'red': '#f1948a', 'red_dim': '#e74c3c',
    'blue': '#85c1e9', 'orange': '#f0b27a', 'purple': '#c39bd3',
    'teal': '#76d7c4', 'gold': '#f7dc6f', 'white': '#f8f9fa',
}

def setup_dark_style():
    plt.rcParams.update({
        'figure.facecolor': DARK['bg'], 'axes.facecolor': DARK['panel'],
        'axes.edgecolor': DARK['border'], 'axes.labelcolor': DARK['text_dim'],
        'text.color': DARK['text'], 'xtick.color': DARK['text_muted'],
        'ytick.color': DARK['text_muted'], 'grid.color': DARK['grid'],
        'grid.alpha': 0.5, 'grid.linewidth': 0.4,
        'font.family': ['Helvetica Neue', 'Arial', 'sans-serif'], 'font.size': 10,
        'legend.facecolor': DARK['panel'], 'legend.edgecolor': DARK['border'],
        'legend.labelcolor': DARK['text_dim'],
    })

# ── Indicators ───────────────────────────────────────────────────────────

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
    return macd_line, signal_line, macd_line - signal_line

def compute_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return sma, sma + std_dev * std, sma - std_dev * std

def compute_fibonacci(high, low):
    diff = high - low
    return {'0.0%': high, '23.6%': high - 0.236 * diff, '38.2%': high - 0.382 * diff,
            '50.0%': high - 0.500 * diff, '61.8%': high - 0.618 * diff,
            '78.6%': high - 0.786 * diff, '100.0%': low}

# ── Drawing Helpers ──────────────────────────────────────────────────────

def draw_candles(ax, df, width=0.6):
    up = df[df.Close >= df.Open]
    down = df[df.Close < df.Open]
    ax.bar(up.index, up.Close - up.Open, bottom=up.Open, width=width, color=DARK['green'], alpha=0.9, zorder=3)
    ax.bar(up.index, up.High - up.Close, bottom=up.Close, width=width*0.15, color=DARK['green'], zorder=3)
    ax.bar(up.index, up.Low - up.Open, bottom=up.Open, width=width*0.15, color=DARK['green'], zorder=3)
    ax.bar(down.index, down.Close - down.Open, bottom=down.Open, width=width, color=DARK['red'], alpha=0.9, zorder=3)
    ax.bar(down.index, down.High - down.Open, bottom=down.Open, width=width*0.15, color=DARK['red'], zorder=3)
    ax.bar(down.index, down.Low - down.Close, bottom=down.Close, width=width*0.15, color=DARK['red'], zorder=3)

def add_watermark(fig):
    fig.text(0.99, 0.01, "FinFlow by WordwideFX", fontsize=8, color=DARK['text_muted'],
             ha='right', va='bottom', alpha=0.6, fontstyle='italic')

def add_header(ax, title, subtitle=None, badge=None):
    ax.set_title(title, fontsize=14, fontweight='600', color=DARK['text'], loc='left', pad=12)
    if subtitle:
        ax.text(1.0, 1.02, subtitle, transform=ax.transAxes, fontsize=8.5, color=DARK['text_muted'], ha='right', va='bottom')
    if badge:
        ax.text(1.0, 1.06, badge, transform=ax.transAxes, fontsize=7, color=DARK['teal'], ha='right', va='bottom',
                fontweight='600', bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK['panel'], edgecolor=DARK['teal'], alpha=0.8, linewidth=0.8))

def format_xaxis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    for label in ax.get_xticklabels():
        label.set_rotation(0)
        label.set_ha('center')

def add_last_price(ax, df, price_format):
    last = float(df.Close.iloc[-1])
    color = DARK['green'] if df.Close.iloc[-1] >= df.Close.iloc[-2] else DARK['red']
    ax.axhline(y=last, color=color, linewidth=0.6, linestyle='--', alpha=0.5, zorder=1)
    label = fmt_price(last, price_format)
    ax.text(df.index[-1] + timedelta(days=2), last, f' {label}',
            fontsize=8, fontweight='600', color=DARK['bg'], va='center', ha='left', zorder=5,
            bbox=dict(boxstyle='round,pad=0.25', facecolor=color, edgecolor='none'))

def get_y_formatter(inst: InstrumentConfig):
    if inst.asset_class == "forex":
        return mticker.FormatStrFormatter(f'%.{inst.price_decimals}f')
    else:
        return mticker.FuncFormatter(lambda x, p: f'${x:,.0f}' if x >= 1000 else f'${x:.2f}')

def get_zone_width(inst: InstrumentConfig):
    """Width of support/resistance highlight zone, proportional to price."""
    if inst.asset_class == "forex":
        return 0.002
    price = max(inst.support, 1)
    return price * 0.004

# ── Chart 1: Beginner ───────────────────────────────────────────────────

def chart_beginner(df, inst: InstrumentConfig):
    setup_dark_style()
    fig, ax = plt.subplots(figsize=(16, 8))
    fig.patch.set_facecolor(DARK['bg'])
    draw_candles(ax, df, width=0.5)

    sma20 = df.Close.rolling(20).mean()
    sma50 = df.Close.rolling(50).mean()
    ax.plot(df.index, sma20, color=DARK['blue'], linewidth=1.8, label='SMA 20', alpha=0.9)
    ax.plot(df.index, sma50, color=DARK['orange'], linewidth=1.8, label='SMA 50', alpha=0.9)

    zw = get_zone_width(inst)
    ax.axhspan(inst.support - zw, inst.support + zw, color=DARK['green'], alpha=0.08, zorder=0)
    ax.axhline(y=inst.support, color=DARK['green'], linewidth=1.2, linestyle='--', alpha=0.6, zorder=1)
    ax.axhspan(inst.resistance - zw, inst.resistance + zw, color=DARK['red'], alpha=0.08, zorder=0)
    ax.axhline(y=inst.resistance, color=DARK['red'], linewidth=1.2, linestyle='--', alpha=0.6, zorder=1)

    s_label = fmt_price(inst.support, inst.price_format)
    r_label = fmt_price(inst.resistance, inst.price_format)
    ax.text(df.index[5], inst.support + zw * 1.5, f'SUPPORT  {s_label}',
            fontsize=9, fontweight='600', color=DARK['green'], alpha=0.9,
            path_effects=[pe.withStroke(linewidth=3, foreground=DARK['bg'])])
    ax.text(df.index[5], inst.resistance + zw * 1.5, f'RESISTANCE  {r_label}',
            fontsize=9, fontweight='600', color=DARK['red'], alpha=0.9,
            path_effects=[pe.withStroke(linewidth=3, foreground=DARK['bg'])])

    add_last_price(ax, df, inst.price_format)
    today = datetime.now().strftime('%B %d, %Y')
    add_header(ax, inst.name, f'Daily  |  {today}', badge='BEGINNER')

    ax.set_ylabel('Price', fontsize=10, color=DARK['text_dim'])
    ax.yaxis.set_major_formatter(get_y_formatter(inst))
    ax.grid(True, alpha=0.3, linewidth=0.3)
    format_xaxis(ax)

    leg = ax.legend(loc='upper left', framealpha=0.9, borderpad=0.8)
    leg.get_frame().set_facecolor(DARK['panel'])
    leg.get_frame().set_edgecolor(DARK['border'])

    add_watermark(fig)
    fig.tight_layout(pad=1.5)
    filename = f'{inst.slug}_beginner.png'
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=200, bbox_inches='tight', facecolor=DARK['bg'], edgecolor='none')
    plt.close(fig)
    print(f"  ✓ {filename}")
    return filename

# ── Chart 2: Intermediate ───────────────────────────────────────────────

def chart_intermediate(df, inst: InstrumentConfig):
    setup_dark_style()
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 11),
                                         gridspec_kw={'height_ratios': [3, 1, 1], 'hspace': 0.08}, sharex=True)
    fig.patch.set_facecolor(DARK['bg'])

    draw_candles(ax1, df, width=0.5)
    bb_mid, bb_upper, bb_lower = compute_bollinger(df.Close)
    ax1.plot(df.index, bb_upper, color=DARK['purple'], linewidth=0.8, alpha=0.6)
    ax1.plot(df.index, bb_mid, color=DARK['purple'], linewidth=0.6, linestyle=':', alpha=0.4)
    ax1.plot(df.index, bb_lower, color=DARK['purple'], linewidth=0.8, alpha=0.6)
    ax1.fill_between(df.index, bb_upper, bb_lower, color=DARK['purple'], alpha=0.04)

    sma50 = df.Close.rolling(50).mean()
    sma200 = df.Close.rolling(200).mean()
    ax1.plot(df.index, sma50, color=DARK['orange'], linewidth=1.3, label='SMA 50', alpha=0.8)
    if sma200.notna().sum() > 20:
        ax1.plot(df.index, sma200, color=DARK['red'], linewidth=1.3, label='SMA 200', alpha=0.8)

    ax1.axhline(y=inst.support, color=DARK['green'], linewidth=0.8, linestyle='--', alpha=0.5)
    ax1.axhline(y=inst.resistance, color=DARK['red'], linewidth=0.8, linestyle='--', alpha=0.5)
    s_label = fmt_price(inst.support, inst.price_format)
    r_label = fmt_price(inst.resistance, inst.price_format)
    ax1.text(df.index[-1] + timedelta(days=1), inst.support, f' S1 {s_label}', fontsize=7.5,
             color=DARK['green'], va='center', fontweight='500')
    ax1.text(df.index[-1] + timedelta(days=1), inst.resistance, f' R1 {r_label}', fontsize=7.5,
             color=DARK['red'], va='center', fontweight='500')

    add_last_price(ax1, df, inst.price_format)
    add_header(ax1, f'{inst.name}  —  Technical Analysis',
               'Daily  |  BB(20,2) + SMA 50/200 + RSI + MACD', badge='INTERMEDIATE')
    ax1.set_ylabel('Price', fontsize=10)
    ax1.yaxis.set_major_formatter(get_y_formatter(inst))
    ax1.grid(True, alpha=0.25, linewidth=0.3)
    leg = ax1.legend(loc='upper left', framealpha=0.9, borderpad=0.6)
    leg.get_frame().set_facecolor(DARK['panel'])
    leg.get_frame().set_edgecolor(DARK['border'])

    # RSI
    rsi = compute_rsi(df.Close)
    ax2.plot(df.index, rsi, color=DARK['blue'], linewidth=1.2)
    ax2.axhline(y=70, color=DARK['red'], linewidth=0.7, linestyle='--', alpha=0.5)
    ax2.axhline(y=30, color=DARK['green'], linewidth=0.7, linestyle='--', alpha=0.5)
    ax2.axhline(y=50, color=DARK['text_muted'], linewidth=0.4, linestyle=':', alpha=0.4)
    ax2.fill_between(df.index, rsi, 70, where=(rsi >= 70), color=DARK['red'], alpha=0.15)
    ax2.fill_between(df.index, rsi, 30, where=(rsi <= 30), color=DARK['green'], alpha=0.15)
    ax2.set_ylabel('RSI(14)', fontsize=9)
    ax2.set_ylim(15, 85)
    ax2.grid(True, alpha=0.2, linewidth=0.3)
    rsi_last = float(rsi.dropna().iloc[-1])
    ax2.text(df.index[-1] + timedelta(days=1), rsi_last, f' {rsi_last:.1f}',
             fontsize=7.5, color=DARK['blue'], va='center', fontweight='500')

    # MACD
    macd_line, signal_line, macd_hist = compute_macd(df.Close)
    colors = [DARK['green'] if v >= 0 else DARK['red'] for v in macd_hist]
    ax3.bar(df.index, macd_hist, color=colors, width=0.5, alpha=0.6, zorder=2)
    ax3.plot(df.index, macd_line, color=DARK['blue'], linewidth=1.1, label='MACD', zorder=3)
    ax3.plot(df.index, signal_line, color=DARK['orange'], linewidth=1.1, label='Signal', zorder=3)
    ax3.axhline(y=0, color=DARK['text_muted'], linewidth=0.4, zorder=1)
    ax3.set_ylabel('MACD', fontsize=9)
    ax3.grid(True, alpha=0.2, linewidth=0.3)
    leg3 = ax3.legend(loc='upper left', framealpha=0.9, borderpad=0.4)
    leg3.get_frame().set_facecolor(DARK['panel'])
    leg3.get_frame().set_edgecolor(DARK['border'])

    format_xaxis(ax3)
    add_watermark(fig)
    fig.tight_layout(pad=1.0)
    filename = f'{inst.slug}_intermediate.png'
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=200, bbox_inches='tight', facecolor=DARK['bg'], edgecolor='none')
    plt.close(fig)
    print(f"  ✓ {filename}")
    return filename

# ── Chart 3: Professional ───────────────────────────────────────────────

def chart_professional(df, inst: InstrumentConfig):
    setup_dark_style()
    fig = plt.figure(figsize=(16, 14))
    fig.patch.set_facecolor(DARK['bg'])
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 0.8, 0.8, 1], hspace=0.08)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax4 = fig.add_subplot(gs[3], sharex=ax1)

    draw_candles(ax1, df, width=0.5)

    # EMA ribbon
    for i, span in enumerate([8, 13, 21, 34, 55]):
        ema = df.Close.ewm(span=span, adjust=False).mean()
        ax1.plot(df.index, ema, linewidth=0.7, alpha=0.25 + i * 0.12, color=DARK['teal'], zorder=2)
    ema200 = df.Close.ewm(span=200, adjust=False).mean()
    if ema200.notna().sum() > 20:
        ax1.plot(df.index, ema200, color=DARK['red'], linewidth=1.5, alpha=0.7, label='EMA 200', zorder=2)

    # Fibonacci
    fib_high = float(df.High.max())
    fib_low = float(df.Low.min())
    fibs = compute_fibonacci(fib_high, fib_low)
    fib_colors = {'0.0%': '#3fb950', '23.6%': '#56d4dd', '38.2%': '#58a6ff',
                  '50.0%': '#d29922', '61.8%': '#d29922', '78.6%': '#f85149', '100.0%': '#da3633'}
    for label, level in fibs.items():
        color = fib_colors.get(label, DARK['text_muted'])
        ax1.axhline(y=level, color=color, linewidth=0.6, linestyle='--', alpha=0.4, zorder=1)
        price_label = fmt_price(level, inst.price_format)
        ax1.text(df.index[-1] + timedelta(days=2), level, f'  {label}  {price_label}',
                 fontsize=7, color=color, va='center', fontweight='500',
                 path_effects=[pe.withStroke(linewidth=2, foreground=DARK['bg'])])

    add_last_price(ax1, df, inst.price_format)
    add_header(ax1, f'{inst.name}  —  Institutional Research',
               'Daily  |  Fibonacci + EMA Ribbon + RSI + MACD + Stochastic', badge='PROFESSIONAL')
    ax1.set_ylabel('Price', fontsize=10)
    ax1.yaxis.set_major_formatter(get_y_formatter(inst))
    ax1.grid(True, alpha=0.2, linewidth=0.3)
    leg = ax1.legend(loc='upper left', framealpha=0.9, borderpad=0.6)
    leg.get_frame().set_facecolor(DARK['panel'])
    leg.get_frame().set_edgecolor(DARK['border'])

    # RSI
    rsi = compute_rsi(df.Close)
    ax2.plot(df.index, rsi, color=DARK['blue'], linewidth=1.0)
    ax2.axhline(y=70, color=DARK['red'], linewidth=0.6, linestyle='--', alpha=0.4)
    ax2.axhline(y=30, color=DARK['green'], linewidth=0.6, linestyle='--', alpha=0.4)
    ax2.fill_between(df.index, rsi, 70, where=(rsi >= 70), color=DARK['red'], alpha=0.12)
    ax2.fill_between(df.index, rsi, 30, where=(rsi <= 30), color=DARK['green'], alpha=0.12)
    ax2.set_ylabel('RSI(14)', fontsize=8); ax2.set_ylim(15, 85)
    ax2.grid(True, alpha=0.15, linewidth=0.3)
    rsi_last = float(rsi.dropna().iloc[-1])
    ax2.text(df.index[-1] + timedelta(days=1), rsi_last, f' {rsi_last:.1f}',
             fontsize=7, color=DARK['blue'], va='center', fontweight='500')

    # MACD
    macd_line, signal_line, macd_hist = compute_macd(df.Close)
    colors = [DARK['green'] if v >= 0 else DARK['red'] for v in macd_hist]
    ax3.bar(df.index, macd_hist, color=colors, width=0.5, alpha=0.5, zorder=2)
    ax3.plot(df.index, macd_line, color=DARK['blue'], linewidth=0.9, label='MACD(12,26,9)', zorder=3)
    ax3.plot(df.index, signal_line, color=DARK['orange'], linewidth=0.9, label='Signal', zorder=3)
    ax3.axhline(y=0, color=DARK['text_muted'], linewidth=0.3, zorder=1)
    ax3.set_ylabel('MACD', fontsize=8)
    ax3.grid(True, alpha=0.15, linewidth=0.3)
    leg3 = ax3.legend(loc='upper left', framealpha=0.9, borderpad=0.3, fontsize=7)
    leg3.get_frame().set_facecolor(DARK['panel']); leg3.get_frame().set_edgecolor(DARK['border'])

    # Stochastic
    low_14 = df.Low.rolling(14).min()
    high_14 = df.High.rolling(14).max()
    stoch_k = 100 * (df.Close - low_14) / (high_14 - low_14)
    stoch_d = stoch_k.rolling(3).mean()
    ax4.plot(df.index, stoch_k, color=DARK['teal'], linewidth=1.0, label='%K(14,3)')
    ax4.plot(df.index, stoch_d, color=DARK['orange'], linewidth=1.0, label='%D(3)')
    ax4.axhline(y=80, color=DARK['red'], linewidth=0.6, linestyle='--', alpha=0.4)
    ax4.axhline(y=20, color=DARK['green'], linewidth=0.6, linestyle='--', alpha=0.4)
    ax4.fill_between(df.index, stoch_k, 80, where=(stoch_k >= 80), color=DARK['red'], alpha=0.1)
    ax4.fill_between(df.index, stoch_k, 20, where=(stoch_k <= 20), color=DARK['green'], alpha=0.1)
    ax4.set_ylabel('Stoch', fontsize=8); ax4.set_ylim(0, 100)
    ax4.grid(True, alpha=0.15, linewidth=0.3)
    leg4 = ax4.legend(loc='upper left', framealpha=0.9, borderpad=0.3, fontsize=7)
    leg4.get_frame().set_facecolor(DARK['panel']); leg4.get_frame().set_edgecolor(DARK['border'])
    stoch_k_last = float(stoch_k.dropna().iloc[-1])
    stoch_d_last = float(stoch_d.dropna().iloc[-1])
    ax4.text(df.index[-1] + timedelta(days=1), stoch_k_last,
             f' {stoch_k_last:.0f}/{stoch_d_last:.0f}',
             fontsize=7, color=DARK['teal'], va='center', fontweight='500')

    format_xaxis(ax4)
    add_watermark(fig)
    fig.tight_layout(pad=1.0)
    filename = f'{inst.slug}_professional.png'
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=200, bbox_inches='tight', facecolor=DARK['bg'], edgecolor='none')
    plt.close(fig)
    print(f"  ✓ {filename}")
    return filename

# ── Scenario Dashboard ──────────────────────────────────────────────────

def chart_scenario(inst: InstrumentConfig):
    setup_dark_style()
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor(DARK['bg'])
    ax.set_facecolor(DARK['bg'])
    ax.axis('off')

    ax.text(0.5, 0.96, f'{inst.name}  SCENARIO ANALYSIS',
            fontsize=22, fontweight='700', ha='center', va='top',
            transform=ax.transAxes, color=DARK['text'])
    today = datetime.now().strftime('%B %d, %Y')
    ax.text(0.5, 0.91, f'{today}  |  Central Variable: Middle East Conflict & Policy Response',
            fontsize=10, ha='center', va='top', transform=ax.transAxes, color=DARK['text_dim'])

    scenarios = inst.scenarios
    box_w = 0.21
    box_h = 0.42
    start_x = 0.04
    y = 0.38

    for i, s in enumerate(scenarios):
        x = start_x + i * 0.24
        rect = FancyBboxPatch((x, y), box_w, box_h, transform=ax.transAxes,
                               boxstyle="round,pad=0.01", facecolor=DARK['panel'],
                               edgecolor=s['color'], linewidth=1.5, alpha=0.9, zorder=2)
        ax.add_patch(rect)

        badge_y = y + box_h - 0.04
        ax.text(x + box_w/2, badge_y + 0.02, s['prob'], fontsize=24, fontweight='700',
                ha='center', va='top', transform=ax.transAxes, color=s['color'])
        ax.text(x + box_w/2, badge_y - 0.06, s['title'], fontsize=10, fontweight='600',
                ha='center', va='top', transform=ax.transAxes, color=DARK['text'])
        ax.text(x + box_w/2, badge_y - 0.12, s['bias'], fontsize=7, fontweight='500',
                ha='center', va='top', transform=ax.transAxes, color=s['color'],
                bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK['bg'],
                          edgecolor=s['color'], linewidth=0.8, alpha=0.9))
        ax.text(x + box_w/2, y + 0.18, 'TARGET', fontsize=7, ha='center', va='top',
                transform=ax.transAxes, color=DARK['text_muted'], fontweight='500')
        ax.text(x + box_w/2, y + 0.13, s['target'], fontsize=11, ha='center', va='top',
                transform=ax.transAxes, color=DARK['text'], fontweight='500', family='monospace')
        ax.text(x + box_w/2, y + 0.06, 'CATALYST', fontsize=7, ha='center', va='top',
                transform=ax.transAxes, color=DARK['text_muted'], fontweight='500')
        ax.text(x + box_w/2, y + 0.02, s['catalyst'], fontsize=8.5, ha='center', va='top',
                transform=ax.transAxes, color=DARK['text_dim'], style='italic')

    add_watermark(fig)
    filename = f'{inst.slug}_scenarios.png'
    fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=200, bbox_inches='tight', facecolor=DARK['bg'], edgecolor='none')
    plt.close(fig)
    print(f"  ✓ {filename}")
    return filename

# ── Public API ───────────────────────────────────────────────────────────

def generate_all_charts(inst: InstrumentConfig, df: pd.DataFrame = None) -> list[str]:
    """Generate all chart types for an instrument. Returns list of filenames."""
    if df is None:
        df = fetch_ohlcv(inst.ticker)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.DatetimeIndex(df.index)

    print(f"\n  Generating {inst.name} charts...")
    files = []
    files.append(chart_beginner(df, inst))
    files.append(chart_intermediate(df, inst))
    files.append(chart_professional(df, inst))
    files.append(chart_scenario(inst))
    return files

# ── Main ─────────────────────────────────────────────────────────────────

def main():
    """Generate charts for all instruments."""
    print("FinFlow Chart Generator — Multi-Instrument")
    print("=" * 50)

    all_files = []
    for slug, inst in INSTRUMENTS.items():
        files = generate_all_charts(inst)
        all_files.extend(files)

    print(f"\n{'=' * 50}")
    print(f"Generated {len(all_files)} charts in {CHARTS_DIR}/")

if __name__ == '__main__':
    main()
