"""
VWAP Micro-Pullback Sniper Bot:
Monitors institutional Volume Weighted Average Price (VWAP).
Executes precision sniper entries when trending prices pull back into VWAP with order flow confirmation.
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal

class VwapScalperBot(BaseBot):
    def __init__(self):
        super().__init__(name="VWAP Sniper")

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        ob = state.get("orderbook", {})

        if indicators is None or indicators.empty or not ob.get("valid"):
            return Signal(self.name, "HOLD", 0.0, "Awaiting market feed")

        latest = indicators.iloc[-1]
        close = latest["close"]
        vwap = latest.get("vwap", close)
        ema_fast = latest["ema_fast"]
        ema_slow = latest["ema_slow"]
        imbalance = ob.get("imbalance", 0.0)

        # Distance from VWAP in %
        dist_pct = abs(close - vwap) / close * 100.0

        # Bullish VWAP Bounce:
        # Price is within 0.06% of VWAP, Fast EMA > Slow EMA, and Buyers stacking orderbook
        if dist_pct <= 0.06 and ema_fast > ema_slow and imbalance > 0.08:
            return Signal(
                bot_name=self.name,
                action="BUY",
                confidence=0.78,
                rationale=f"Bullish VWAP Retest: Price (${close:.4f}) within {dist_pct:.3f}% of VWAP (${vwap:.4f}) with buyer wall ({imbalance:+.2f})",
                entry_price=ob.get("best_bid")
            )

        # Bearish VWAP Rejection:
        # Price is within 0.06% of VWAP, Fast EMA < Slow EMA, and Sellers stacking orderbook
        if dist_pct <= 0.06 and ema_fast < ema_slow and imbalance < -0.08:
            return Signal(
                bot_name=self.name,
                action="SELL",
                confidence=0.78,
                rationale=f"Bearish VWAP Rejection: Price (${close:.4f}) within {dist_pct:.3f}% of VWAP (${vwap:.4f}) with seller wall ({imbalance:+.2f})",
                entry_price=ob.get("best_ask")
            )

        return Signal(
            bot_name=self.name,
            action="HOLD",
            confidence=0.5,
            rationale=f"Price is {dist_pct:.2f}% away from VWAP (${vwap:.4f}). Waiting for pullback."
        )
