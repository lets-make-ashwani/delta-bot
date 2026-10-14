"""
Market Analyst Bot:
Continuously digests tick data, candle indicators, and orderbook structure.
Identifies the active market regime:
- STRONG_UPTREND
- STRONG_DOWNTREND
- RANGING / CHOPPY
- HIGH_VOLATILITY_BURST
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal

class MarketAnalystBot(BaseBot):
    def __init__(self):
        super().__init__(name="Market Analyst")

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        ob = state.get("orderbook")
        
        if indicators is None or indicators.empty or not ob.get("valid"):
            return Signal(
                bot_name=self.name,
                action="HOLD",
                confidence=0.0,
                rationale="Waiting for market data & orderbook feed."
            )

        latest = indicators.iloc[-1]
        prev = indicators.iloc[-2] if len(indicators) > 1 else latest
        
        ema_fast = latest["ema_fast"]
        ema_slow = latest["ema_slow"]
        rsi = latest["rsi"]
        imbalance = ob["imbalance"]
        spread_pct = ob["spread_pct"]

        # Determine Regime
        ema_gap = abs(ema_fast - ema_slow) / latest["close"] * 100.0
        
        if ema_gap > 0.08 and ema_fast > ema_slow and rsi > 52:
            regime = "STRONG_UPTREND"
        elif ema_gap > 0.08 and ema_fast < ema_slow and rsi < 48:
            regime = "STRONG_DOWNTREND"
        elif latest["atr"] / latest["close"] * 100.0 > 0.15:
            regime = "HIGH_VOLATILITY"
        else:
            regime = "RANGING_CHOP"

        state["regime"] = regime
        state["latest_candle"] = latest
        
        rationale = (f"Regime: {regime} | EMA Fast: {ema_fast:.4f}, Slow: {ema_slow:.4f} | "
                     f"RSI: {rsi:.1f} | Book Imbalance: {imbalance:+.2f} | Spread: {spread_pct:.3f}%")

        return Signal(
            bot_name=self.name,
            action="HOLD",  # Market analyst provides context, doesn't vote directly on execution
            confidence=0.8,
            rationale=rationale
        )
