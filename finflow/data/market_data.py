"""
Market data fetcher with technical indicator computation and caching.
Uses yfinance for OHLCV data.
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def fetch_ohlcv(ticker: str, period: str = "1y", use_cache: bool = True) -> pd.DataFrame:
    """Fetch OHLCV data from yfinance with CSV caching for offline fallback."""
    cache_file = os.path.join(CACHE_DIR, f"{ticker.replace('=', '_').replace('/', '_')}.csv")

    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.DatetimeIndex(df.index)

        if len(df) > 0:
            df.to_csv(cache_file)
            return df
    except Exception:
        pass

    # Fallback to cache
    if use_cache and os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        df.index = pd.DatetimeIndex(df.index)
        return df

    raise RuntimeError(f"Failed to fetch data for {ticker} and no cache available")


def compute_indicators(df: pd.DataFrame) -> dict:
    """Compute technical indicators from OHLCV data. Returns a dict of Series/values."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    indicators = {}

    # Moving averages
    indicators["sma_20"] = close.rolling(20).mean()
    indicators["sma_50"] = close.rolling(50).mean()
    indicators["sma_200"] = close.rolling(200).mean()
    indicators["ema_20"] = close.ewm(span=20, adjust=False).mean()
    indicators["ema_50"] = close.ewm(span=50, adjust=False).mean()
    indicators["ema_200"] = close.ewm(span=200, adjust=False).mean()

    # RSI (14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(14, min_periods=14).mean()
    avg_loss = loss.rolling(14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    indicators["rsi"] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    indicators["macd_line"] = ema12 - ema26
    indicators["macd_signal"] = indicators["macd_line"].ewm(span=9, adjust=False).mean()
    indicators["macd_histogram"] = indicators["macd_line"] - indicators["macd_signal"]

    # Bollinger Bands (20, 2)
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    indicators["bb_upper"] = sma20 + 2 * std20
    indicators["bb_middle"] = sma20
    indicators["bb_lower"] = sma20 - 2 * std20

    # Stochastic (14, 3)
    low_14 = low.rolling(14).min()
    high_14 = high.rolling(14).max()
    indicators["stoch_k"] = 100 * (close - low_14) / (high_14 - low_14)
    indicators["stoch_d"] = indicators["stoch_k"].rolling(3).mean()

    # ATR (14)
    tr = pd.DataFrame({
        "hl": high - low,
        "hc": abs(high - close.shift(1)),
        "lc": abs(low - close.shift(1)),
    }).max(axis=1)
    indicators["atr"] = tr.rolling(14).mean()

    # Current values (last row)
    last = {}
    for key, val in indicators.items():
        if isinstance(val, pd.Series):
            v = val.dropna()
            last[key] = float(v.iloc[-1]) if len(v) > 0 else None
        else:
            last[key] = val
    indicators["current"] = last

    return indicators


def get_price_summary(df: pd.DataFrame, indicators: dict) -> dict:
    """Get a concise price summary for agent context."""
    cur = indicators["current"]
    last_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])
    change_pct = ((last_close - prev_close) / prev_close) * 100

    return {
        "last_close": last_close,
        "daily_change_pct": round(change_pct, 2),
        "high_52w": float(df["High"].max()),
        "low_52w": float(df["Low"].min()),
        "rsi": round(cur["rsi"], 1) if cur["rsi"] else None,
        "macd_histogram": round(cur["macd_histogram"], 4) if cur["macd_histogram"] else None,
        "macd_signal": "bullish" if cur["macd_histogram"] and cur["macd_histogram"] > 0 else "bearish",
        "stoch_k": round(cur["stoch_k"], 1) if cur["stoch_k"] else None,
        "atr": round(cur["atr"], 4) if cur["atr"] else None,
        "above_sma_50": last_close > cur["sma_50"] if cur["sma_50"] else None,
        "above_sma_200": last_close > cur["sma_200"] if cur["sma_200"] else None,
        "bb_position": _bb_position(last_close, cur),
    }


def _bb_position(price, cur):
    """Where price sits relative to Bollinger Bands."""
    if not cur.get("bb_upper") or not cur.get("bb_lower"):
        return "unknown"
    bb_range = cur["bb_upper"] - cur["bb_lower"]
    if bb_range <= 0:
        return "unknown"
    pct = (price - cur["bb_lower"]) / bb_range
    if pct > 0.8:
        return "near upper band (overbought zone)"
    elif pct < 0.2:
        return "near lower band (oversold zone)"
    else:
        return "mid-range"
