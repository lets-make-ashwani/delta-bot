"""
Mean Reversion Scalper Bot:
Specialized in fading extremes during choppy or ranging market conditions.
Enters at outer Bollinger Bands when RSI is stretched.
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal

class MeanReversionBot(BaseBot):
    def __init__(self):
        super().__init__(name="Mean Reversion")

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        ob = state.get("orderbook")
        regime = state.get("regime", "RANGING_CHOP")

        if indicators is None or indicators.empty or not ob.get("valid"):
            return Signal(self.name, "HOLD", 0.0, "Missing data")

        # Mean reversion is strictly avoided during aggressive trend runs!
        if regime in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
            return Signal(
                bot_name=self.name,
                action="HOLD",
                confidence=0.7,
                rationale="Fading prohibited during strong directional trend."
            )

        latest = indicators.iloc[-1]
        rsi = latest["rsi"]
        close = latest["close"]
        bb_upper = latest["bb_upper"]
        bb_lower = latest["bb_lower"]
        best_bid = ob["best_bid"]
        best_ask = ob["best_ask"]

        # Oversold Bounce: Price at or below lower Bollinger Band, RSI < 32
        if close <= bb_lower * 1.0005 and rsi < 32:
            return Signal(
                bot_name=self.name,
                action="BUY",
                confidence=0.70,
                rationale=f"Oversold Bounce: Close (${close:.4f}) <= Lower BB (${bb_lower:.4f}) with RSI {rsi:.1f}",
                entry_price=best_bid
            )

        # Overbought Rejection: Price at or above upper Bollinger Band, RSI > 68
        if close >= bb_upper * 0.9995 and rsi > 68:
            return Signal(
                bot_name=self.name,
                action="SELL",
                confidence=0.70,
                rationale=f"Overbought Rejection: Close (${close:.4f}) >= Upper BB (${bb_upper:.4f}) with RSI {rsi:.1f}",
                entry_price=best_ask
            )

        return Signal(
            bot_name=self.name,
            action="HOLD",
            confidence=0.5,
            rationale="Price within normal Bollinger envelope."
        )
