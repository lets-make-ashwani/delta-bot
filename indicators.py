"""
Technical Indicators and Microstructure Metrics for Delta 100x Scalping Swarm.
Computes:
- EMA (9, 21)
- RSI (14)
- Bollinger Bands (20, 2)
- ATR (14)
- VWAP (Session Volume Weighted Average Price)
- Wick lengths & Candle anatomy (for liquidity sweep detection)
- Rolling 15-period High & Low
- Order Book Spread & Imbalance
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any

def calculate_indicators(candles: List[Dict[str, Any]]) -> pd.DataFrame:
    """Transforms raw Delta Exchange candles into a pandas DataFrame with quantitative indicators."""
    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.sort_values("time").reset_index(drop=True)
    
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = df[col].astype(float)

    # 1. Exponential Moving Averages (EMA 9 and EMA 21)
    df["ema_fast"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=21, adjust=False).mean()
    df["ema_trend"] = np.where(df["ema_fast"] > df["ema_slow"], 1, -1)

    # 2. Relative Strength Index (RSI 14)
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss.replace(0, np.nan))
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)

    # 3. Bollinger Bands (20, 2)
    df["bb_mid"] = df["close"].rolling(window=20).mean()
    df["bb_std"] = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_mid"] + (df["bb_std"] * 2)
    df["bb_lower"] = df["bb_mid"] - (df["bb_std"] * 2)

    # 4. Average True Range (ATR 14)
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean().bfill()

    # 5. Volume Weighted Average Price (VWAP)
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol_price = (typical_price * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum()
    df["vwap"] = np.where(cum_vol > 0, cum_vol_price / cum_vol, df["close"])

    # 6. Rolling 15-period High and Low (for Liquidity Sweeps)
    df["high_15"] = df["high"].rolling(15).max().shift(1)
    df["low_15"] = df["low"].rolling(15).min().shift(1)

    # 7. Candle Anatomy & Wicks (Upper Wick, Lower Wick, Body)
    candle_range = (df["high"] - df["low"]).replace(0, 0.0001)
    candle_body_top = df[["open", "close"]].max(axis=1)
    candle_body_bottom = df[["open", "close"]].min(axis=1)
    
    df["upper_wick_ratio"] = (df["high"] - candle_body_top) / candle_range
    df["lower_wick_ratio"] = (candle_body_bottom - df["low"]) / candle_range
    df["body_ratio"] = (candle_body_top - candle_body_bottom) / candle_range

    # 8. Volume Surge
    df["vol_sma"] = df["volume"].rolling(window=20).mean()
    df["vol_surge"] = df["volume"] > (df["vol_sma"] * 1.4)

    return df


def calculate_orderbook_metrics(quotes: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates spread, depth imbalance, and top-of-book walls."""
    if not quotes:
        return {"spread_pct": 0.0, "imbalance": 0.0, "valid": False}

    best_bid = float(quotes.get("best_bid") or 0.0)
    best_ask = float(quotes.get("best_ask") or 0.0)
    bid_size = float(quotes.get("bid_size") or 0.0)
    ask_size = float(quotes.get("ask_size") or 0.0)

    if best_bid <= 0 or best_ask <= 0:
        return {"spread_pct": 0.0, "imbalance": 0.0, "valid": False}

    spread = best_ask - best_bid
    mid_price = (best_ask + best_bid) / 2.0
    spread_pct = (spread / mid_price) * 100.0

    total_size = bid_size + ask_size
    imbalance = (bid_size - ask_size) / total_size if total_size > 0 else 0.0

    # Detect Wall Dominance: Is one side more than 2.5x larger?
    has_bid_wall = bid_size > (ask_size * 2.5) and bid_size > 2000
    has_ask_wall = ask_size > (bid_size * 2.5) and ask_size > 2000

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid_price,
        "spread_pct": round(spread_pct, 4),
        "bid_size": bid_size,
        "ask_size": ask_size,
        "imbalance": round(imbalance, 3),
        "has_bid_wall": has_bid_wall,
        "has_ask_wall": has_ask_wall,
        "valid": True
    }
