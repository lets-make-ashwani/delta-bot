"""
Strategy Generator & Adaptation Bot (The Meta-Quant):
Analyzes market conditions and dynamically generates/tunes strategy parameters:
- Adjusts weights between Momentum and Mean Reversion.
- Adapts Stop-Loss and Take-Profit distances dynamically to market volatility.
- Prevents overtrading and evolves rules based on market behavior.
"""

from typing import Dict, Any
from bots.base_bot import BaseBot, Signal
from config import config

class StrategyGeneratorBot(BaseBot):
    def __init__(self):
        super().__init__(name="Strategy Generator")
        self.strategy_profile = {
            "mode": "BALANCED",
            "momentum_weight": 0.5,
            "mean_reversion_weight": 0.5,
            "dynamic_sl_pct": config.STOP_LOSS_PCT,
            "dynamic_tp_pct": config.TAKE_PROFIT_PCT,
            "min_confidence_threshold": 0.65
        }

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        regime = state.get("regime", "RANGING_CHOP")
        
        if indicators is None or indicators.empty:
            return Signal(self.name, "HOLD", 0.0, "Awaiting market history")

        latest = indicators.iloc[-1]
        atr = latest.get("atr", 0.001)
        close = latest["close"]
        volatility_ratio = (atr / close) * 100.0  # ATR in % of price

        # 1. Self-Adaptation Logic:
        # High volatility -> Tighten stop loss because at 100x, sudden wicks can liquidate!
        if volatility_ratio > 0.20:
            self.strategy_profile["mode"] = "VOLATILITY_DEFENSE"
            self.strategy_profile["momentum_weight"] = 0.7
            self.strategy_profile["mean_reversion_weight"] = 0.3
            self.strategy_profile["dynamic_sl_pct"] = 0.20  # Ultra-tight 0.20% stop
            self.strategy_profile["dynamic_tp_pct"] = 0.60  # Target bigger 0.60% pop
            self.strategy_profile["min_confidence_threshold"] = 0.70

        elif regime in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
            self.strategy_profile["mode"] = "TREND_RUNNER"
            self.strategy_profile["momentum_weight"] = 0.85
            self.strategy_profile["mean_reversion_weight"] = 0.15
            self.strategy_profile["dynamic_sl_pct"] = 0.25
            self.strategy_profile["dynamic_tp_pct"] = 0.65
            self.strategy_profile["min_confidence_threshold"] = 0.62

        else: # Ranging / Choppy
            self.strategy_profile["mode"] = "RANGE_HARVESTER"
            self.strategy_profile["momentum_weight"] = 0.2
            self.strategy_profile["mean_reversion_weight"] = 0.8
            self.strategy_profile["dynamic_sl_pct"] = 0.22
            self.strategy_profile["dynamic_tp_pct"] = 0.45
            self.strategy_profile["min_confidence_threshold"] = 0.65

        state["strategy_profile"] = self.strategy_profile

        rationale = (f"Adapted Strategy: [{self.strategy_profile['mode']}] | "
                     f"MOM Weight: {self.strategy_profile['momentum_weight']:.1f}, "
                     f"MR Weight: {self.strategy_profile['mean_reversion_weight']:.1f} | "
                     f"Tuned SL: {self.strategy_profile['dynamic_sl_pct']:.2f}%, "
                     f"TP: {self.strategy_profile['dynamic_tp_pct']:.2f}%")

        return Signal(
            bot_name=self.name,
            action="HOLD",
            confidence=0.85,
            rationale=rationale
        )

    def tune_active_position_brackets(self, pos: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically adjusts Stop-Loss and Take-Profit of an active position according to real-time analysis:
        1. Breakeven Lock: Ratchets SL to entry price once trade reaches +0.18% profit.
        2. Dynamic Trailing SL: Trails behind price peak using ATR buffer to lock in progressive profit.
        3. Adaptive Target Extension: Widens TP target up to +0.85% during strong trend velocity & high AI confidence.
        4. Wall Resistance Sniping: Front-runs orderbook depth walls just below heavy resistance.
        5. Momentum Exhaustion Tightening: Pulls target closer when RSI is overstretched (>75).
        """
        side = pos.get("side", "BUY")
        entry = float(pos.get("entry_price", 0.0))
        current_sl = float(pos.get("stop_loss", 0.0))
        current_tp = float(pos.get("take_profit", 0.0))
        mark = float(state.get("mark_price", entry))
        
        if entry <= 0 or mark <= 0:
            return {"updated": False, "old_sl": current_sl, "new_sl": current_sl, "old_tp": current_tp, "new_tp": current_tp, "adjustments": []}

        # Track watermarks across trade lifecycle
        if "highest_price" not in pos or mark > pos["highest_price"]:
            pos["highest_price"] = mark
        if "lowest_price" not in pos or mark < pos["lowest_price"]:
            pos["lowest_price"] = mark
            
        peak_price = pos["highest_price"]
        trough_price = pos["lowest_price"]
        
        # Rounding helper for tick size
        tick_size = 0.0001
        def round_tick(val: float) -> float:
            return round(round(val / tick_size) * tick_size, 4)

        indicators = state.get("indicators")
        ob = state.get("orderbook", {})
        regime = state.get("regime", "RANGING_CHOP")
        jarvis = state.get("jarvis_ai", {})
        q_score = jarvis.get("quant_score", 0)
        
        latest_ind = indicators.iloc[-1] if indicators is not None and not indicators.empty else {}
        rsi = latest_ind.get("rsi", 50)
        atr = latest_ind.get("atr", 0.001)
        vol_surge = latest_ind.get("vol_surge", False)

        new_sl = current_sl
        new_tp = current_tp
        adjustments = []

        # =============================================================
        # PART 1: DYNAMIC STOP-LOSS ADJUSTMENTS (Trailing & Defense)
        # =============================================================
        if side == "BUY":
            gain_pct = (mark - entry) / entry * 100.0
            peak_gain_pct = (peak_price - entry) / entry * 100.0

            # Level 1: Breakeven Lock at +0.18% profit
            breakeven_price = round_tick(entry * 1.0002) # covers fee
            if peak_gain_pct >= 0.18 and new_sl < breakeven_price:
                new_sl = breakeven_price
                adjustments.append(f"SL ratcheted to BREAKEVEN (${new_sl} / risk-free trade)")

            # Level 2: Progressive Profit Lock at +0.35%
            if peak_gain_pct >= 0.35:
                lock_price = round_tick(entry * 1.0018) # lock in +0.18% net profit
                if new_sl < lock_price:
                    new_sl = lock_price
                    adjustments.append(f"SL locked in +0.18% guaranteed profit (${new_sl})")

            # Level 3: Dynamic Trailing SL behind peak at +0.50%+
            if peak_gain_pct >= 0.50:
                trailing_level = round_tick(peak_price * 0.9984) # 0.16% buffer behind peak
                if new_sl < trailing_level:
                    new_sl = trailing_level
                    adjustments.append(f"Dynamic Trailing SL followed peak to ${new_sl}")

            # Level 4: Early Defensive Tightening if Orderbook seller wall emerges
            if gain_pct < 0 and (rsi < 35 or q_score <= -40) and ob.get("has_ask_wall"):
                defensive_sl = round_tick(entry * 0.9985) # Cut stop loss from -0.25% to -0.15%
                if defensive_sl > new_sl:
                    new_sl = defensive_sl
                    adjustments.append(f"SL tightened defensively to ${new_sl} due to heavy ask wall")

        else: # SELL
            gain_pct = (entry - mark) / entry * 100.0
            peak_gain_pct = (entry - trough_price) / entry * 100.0

            # Level 1: Breakeven Lock at +0.18% profit
            breakeven_price = round_tick(entry * 0.9998)
            if peak_gain_pct >= 0.18 and (new_sl == 0 or new_sl > breakeven_price):
                new_sl = breakeven_price
                adjustments.append(f"SL ratcheted to BREAKEVEN (${new_sl} / risk-free trade)")

            # Level 2: Progressive Profit Lock at +0.35%
            if peak_gain_pct >= 0.35:
                lock_price = round_tick(entry * 0.9982)
                if new_sl > lock_price:
                    new_sl = lock_price
                    adjustments.append(f"SL locked in +0.18% guaranteed profit (${new_sl})")

            # Level 3: Dynamic Trailing SL above trough at +0.50%+
            if peak_gain_pct >= 0.50:
                trailing_level = round_tick(trough_price * 1.0016)
                if new_sl > trailing_level:
                    new_sl = trailing_level
                    adjustments.append(f"Dynamic Trailing SL followed trough to ${new_sl}")

            # Level 4: Early Defensive Tightening
            if gain_pct < 0 and (rsi > 65 or q_score >= 40) and ob.get("has_bid_wall"):
                defensive_sl = round_tick(entry * 1.0015)
                if defensive_sl < new_sl:
                    new_sl = defensive_sl
                    adjustments.append(f"SL tightened defensively to ${new_sl} due to heavy bid wall")

        # =============================================================
        # PART 2: ADAPTIVE TARGET (TAKE-PROFIT) ADJUSTMENTS
        # =============================================================
        if side == "BUY":
            # Target Rule A: Trend Velocity Expansion
            if regime == "STRONG_UPTREND" and vol_surge and q_score >= 50:
                extended_tp = round_tick(entry * 1.0085)
                if extended_tp > new_tp:
                    new_tp = extended_tp
                    adjustments.append(f"TP expanded to ${new_tp} (+0.85% Trend Runner)")

            # Target Rule B: Order Book Resistance Sniping (front-run the Ask Wall)
            if ob.get("has_ask_wall"):
                ask_wall_price = float(ob.get("best_ask", 0.0))
                if ask_wall_price > mark and ask_wall_price < new_tp:
                    sniped_tp = round_tick(ask_wall_price - tick_size)
                    if sniped_tp > mark:
                        new_tp = sniped_tp
                        adjustments.append(f"TP adjusted to ${new_tp} to front-run Ask Wall before rejection")

            # Target Rule C: RSI Overbought Exhaustion Tightening
            if rsi > 76 and mark >= entry * 1.0035:
                tightened_tp = round_tick(mark + tick_size)
                if tightened_tp < new_tp:
                    new_tp = tightened_tp
                    adjustments.append(f"TP tightened to ${new_tp} to secure gains before RSI {rsi:.1f} exhaustion")

        else: # SELL
            # Target Rule A: Trend Velocity Expansion
            if regime == "STRONG_DOWNTREND" and vol_surge and q_score <= -50:
                extended_tp = round_tick(entry * 0.9915)
                if extended_tp < new_tp:
                    new_tp = extended_tp
                    adjustments.append(f"TP expanded to ${new_tp} (-0.85% Trend Runner)")

            # Target Rule B: Order Book Support Sniping
            if ob.get("has_bid_wall"):
                bid_wall_price = float(ob.get("best_bid", 0.0))
                if bid_wall_price < mark and bid_wall_price > new_tp:
                    sniped_tp = round_tick(bid_wall_price + tick_size)
                    if sniped_tp < mark:
                        new_tp = sniped_tp
                        adjustments.append(f"TP adjusted to ${new_tp} to front-run Bid Wall before bounce")

            # Target Rule C: RSI Oversold Exhaustion Tightening
            if rsi < 24 and mark <= entry * 0.9965:
                tightened_tp = round_tick(mark - tick_size)
                if tightened_tp > new_tp:
                    new_tp = tightened_tp
                    adjustments.append(f"TP tightened to ${new_tp} to secure gains before RSI {rsi:.1f} bounce")

        # Apply adjustments
        updated = False
        if new_sl != current_sl or new_tp != current_tp:
            pos["stop_loss"] = new_sl
            pos["take_profit"] = new_tp
            updated = True

        return {
            "updated": updated,
            "old_sl": current_sl,
            "new_sl": new_sl,
            "old_tp": current_tp,
            "new_tp": new_tp,
            "adjustments": adjustments
        }
