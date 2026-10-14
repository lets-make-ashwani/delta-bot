"""
Order Book Wall Scalper Bot:
Monitors live L2 microstructure and depth volume walls.
Detects heavy wall absorption and front-runs defending walls with Maker limit entries.
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal

class OrderBookWallScalperBot(BaseBot):
    def __init__(self):
        super().__init__(name="Order Book Wall Scalper")

    def analyze(self, state: Dict[str, Any]) -> Signal:
        ob = state.get("orderbook", {})

        if not ob or not ob.get("valid"):
            return Signal(self.name, "HOLD", 0.0, "Awaiting L2 orderbook feed")

        has_bid_wall = ob.get("has_bid_wall", False)
        has_ask_wall = ob.get("has_ask_wall", False)
        imbalance = ob.get("imbalance", 0.0)
        spread_pct = ob.get("spread_pct", 0.0)
        bid_size = ob.get("bid_size", 0)
        ask_size = ob.get("ask_size", 0)

        # 1. Major Buyer Wall Defense
        if has_bid_wall and imbalance >= 0.30 and spread_pct <= 0.02:
            return Signal(
                bot_name=self.name,
                action="BUY",
                confidence=0.75,
                rationale=f"Heavy Bid Wall Defended: Bid Size ({bid_size:,.0f}) is >2.5x Ask ({ask_size:,.0f}) with {imbalance:+.2f} skew!",
                entry_price=ob.get("best_bid")
            )

        # 2. Major Seller Wall Defense
        if has_ask_wall and imbalance <= -0.30 and spread_pct <= 0.02:
            return Signal(
                bot_name=self.name,
                action="SELL",
                confidence=0.75,
                rationale=f"Heavy Ask Wall Defended: Ask Size ({ask_size:,.0f}) is >2.5x Bid ({bid_size:,.0f}) with {imbalance:+.2f} skew!",
                entry_price=ob.get("best_ask")
            )

        return Signal(
            bot_name=self.name,
            action="HOLD",
            confidence=0.5,
            rationale=f"Balanced book depth (Bid: {bid_size:,.0f} vs Ask: {ask_size:,.0f}). No wall imbalance."
        )
