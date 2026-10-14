"""
Liquidity Wick Sweep Scalper Bot:
Detects institutional stop-hunts / fakeouts at 15-period range highs and lows.
Enters immediately when price wicks beyond a key level and closes back inside with a long rejection shadow.
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal

class WickSweepScalperBot(BaseBot):
    def __init__(self):
        super().__init__(name="Liquidity Wick Sweep")

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        ob = state.get("orderbook", {})

        if indicators is None or indicators.empty or not ob.get("valid"):
            return Signal(self.name, "HOLD", 0.0, "Awaiting candle data")

        latest = indicators.iloc[-1]
        high_15 = latest.get("high_15")
        low_15 = latest.get("low_15")

        if not high_15 or not low_15 or pd_isna(high_15) or pd_isna(low_15):
            return Signal(self.name, "HOLD", 0.5, "Building 15-period liquidity levels...")

        close = latest["close"]
        high = latest["high"]
        low = latest["low"]
        upper_wick = latest.get("upper_wick_ratio", 0.0)
        lower_wick = latest.get("lower_wick_ratio", 0.0)
        imbalance = ob.get("imbalance", 0.0)

        # 1. Bearish Liquidity Sweep (Swept High, Rejected Back Down)
        # Price spiked above the 15-candle high, but candle closed below with >=40% upper wick
        if high > high_15 and close < high_15 and upper_wick >= 0.40:
            return Signal(
                bot_name=self.name,
                action="SELL",
                confidence=0.82,
                rationale=f"Bearish Stop-Hunt Sweep: High (${high:.4f}) broke 15m high (${high_15:.4f}) but rejected ({upper_wick*100:.0f}% wick)!",
                entry_price=ob.get("best_ask")
            )

        # 2. Bullish Liquidity Sweep (Swept Low, Absorbed Back Up)
        # Price flushed below the 15-candle low, but candle closed above with >=40% lower wick
        if low < low_15 and close > low_15 and lower_wick >= 0.40:
            return Signal(
                bot_name=self.name,
                action="BUY",
                confidence=0.82,
                rationale=f"Bullish Liquidity Sweep: Low (${low:.4f}) flushed 15m low (${low_15:.4f}) and absorbed ({lower_wick*100:.0f}% wick)!",
                entry_price=ob.get("best_bid")
            )

        return Signal(
            bot_name=self.name,
            action="HOLD",
            confidence=0.5,
            rationale="No liquidity sweep detected at range extremes."
        )

def pd_isna(val):
    try:
        import pandas as pd
        return pd.isna(val)
    except Exception:
        return False
