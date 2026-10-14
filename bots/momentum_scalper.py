"""
Momentum Scalper Bot:
Specialized in capturing micro-trend continuation and volatility breakouts.
Focuses on entering fast moves before exhaustion.
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal

class MomentumScalperBot(BaseBot):
    def __init__(self):
        super().__init__(name="Momentum Scalper")

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        ob = state.get("orderbook")
        regime = state.get("regime", "RANGING_CHOP")

        if indicators is None or indicators.empty or not ob.get("valid"):
            return Signal(self.name, "HOLD", 0.0, "Missing data")

        latest = indicators.iloc[-1]
        prev = indicators.iloc[-2] if len(indicators) > 1 else latest
        
        rsi = latest["rsi"]
        imbalance = ob["imbalance"]
        vol_surge = latest["vol_surge"]
        best_bid = ob["best_bid"]
        best_ask = ob["best_ask"]

        # Long Trigger:
        # 1. EMA fast > slow
        # 2. RSI in momentum sweet spot (52 - 68)
        # 3. Buyers dominating top of book (imbalance > +0.10)
        # 4. In UPTREND or Volume surge
        is_long = (
            latest["ema_fast"] > latest["ema_slow"] and
            52 <= rsi <= 68 and
            imbalance > 0.10 and
            (regime == "STRONG_UPTREND" or vol_surge)
        )

        # Short Trigger:
        # 1. EMA fast < slow
        # 2. RSI in momentum sweet spot (32 - 48)
        # 3. Sellers dominating top of book (imbalance < -0.10)
        # 4. In DOWNTREND or Volume surge
        is_short = (
            latest["ema_fast"] < latest["ema_slow"] and
            32 <= rsi <= 48 and
            imbalance < -0.10 and
            (regime == "STRONG_DOWNTREND" or vol_surge)
        )

        if is_long:
            conf = 0.75 if vol_surge else 0.65
            return Signal(
                bot_name=self.name,
                action="BUY",
                confidence=conf,
                rationale=f"Bullish micro-breakout: EMA fast > slow, RSI {rsi:.1f}, Buyer Book Imbalance {imbalance:+.2f}",
                entry_price=best_bid  # Limit post at best bid
            )
        elif is_short:
            conf = 0.75 if vol_surge else 0.65
            return Signal(
                bot_name=self.name,
                action="SELL",
                confidence=conf,
                rationale=f"Bearish micro-breakdown: EMA fast < slow, RSI {rsi:.1f}, Seller Book Imbalance {imbalance:+.2f}",
                entry_price=best_ask  # Limit post at best ask
            )

        return Signal(
            bot_name=self.name,
            action="HOLD",
            confidence=0.5,
            rationale="No clear momentum breakout setup."
        )
