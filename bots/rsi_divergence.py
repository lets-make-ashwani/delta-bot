"""
RSI Divergence Scalper Bot:
Detects early momentum exhaustion before prices turn.
Identifies Bullish and Bearish divergences between price action and RSI.
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal

class RsiDivergenceBot(BaseBot):
    def __init__(self):
        super().__init__(name="RSI Divergence")

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        ob = state.get("orderbook", {})

        if indicators is None or len(indicators) < 20 or not ob.get("valid"):
            return Signal(self.name, "HOLD", 0.0, "Building divergence history...")

        latest = indicators.iloc[-1]
        prev_window = indicators.iloc[-15:-3]

        curr_close = latest["close"]
        curr_rsi = latest["rsi"]

        # Find previous swing low and high
        min_prev_idx = prev_window["low"].idxmin()
        prev_low_price = prev_window.loc[min_prev_idx, "low"]
        prev_low_rsi = prev_window.loc[min_prev_idx, "rsi"]

        max_prev_idx = prev_window["high"].idxmax()
        prev_high_price = prev_window.loc[max_prev_idx, "high"]
        prev_high_rsi = prev_window.loc[max_prev_idx, "rsi"]

        # 1. Bullish Divergence:
        # Price makes Lower Low (or equal), but RSI makes Higher Low by at least 3 points, with RSI in oversold/moderate zone (< 45)
        if latest["low"] <= prev_low_price * 1.0002 and curr_rsi >= prev_low_rsi + 3.0 and curr_rsi <= 45:
            return Signal(
                bot_name=self.name,
                action="BUY",
                confidence=0.78,
                rationale=f"Bullish RSI Divergence: Price Low (${latest['low']:.4f} <= ${prev_low_price:.4f}) while RSI rose ({curr_rsi:.1f} > {prev_low_rsi:.1f})!",
                entry_price=ob.get("best_bid")
            )

        # 2. Bearish Divergence:
        # Price makes Higher High (or equal), but RSI makes Lower High by at least 3 points, with RSI in overbought/moderate zone (> 55)
        if latest["high"] >= prev_high_price * 0.9998 and curr_rsi <= prev_high_rsi - 3.0 and curr_rsi >= 55:
            return Signal(
                bot_name=self.name,
                action="SELL",
                confidence=0.78,
                rationale=f"Bearish RSI Divergence: Price High (${latest['high']:.4f} >= ${prev_high_price:.4f}) while RSI fell ({curr_rsi:.1f} < {prev_high_rsi:.1f})!",
                entry_price=ob.get("best_ask")
            )

        return Signal(
            bot_name=self.name,
            action="HOLD",
            confidence=0.5,
            rationale=f"RSI ({curr_rsi:.1f}) moving in tandem with price. No divergence."
        )
