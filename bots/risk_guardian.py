"""
Chief Risk Officer (Risk Guardian Bot):
Holds absolute veto authority over trade execution.
Enforces:
1. Multi-bullet capital protection (never bet 100% of balance on a single trade).
2. Tight Stop-Loss calculations before Delta liquidation engine triggers.
3. Spread and Slippage gating.
4. Position limits (strictly 1 active scalp at a time).
"""

import time
import math
import logging
from typing import Dict, Any, Optional
from bots.base_bot import BaseBot, Signal
from config import config

logger = logging.getLogger("RiskGuardian")

class RiskGuardianBot(BaseBot):
    def __init__(self):
        super().__init__(name="Chief Risk Officer")
        self.last_trade_time = 0.0
        self.cooldown_sec = 45.0           # Minimum 45s between trades to prevent churning
        self.consecutive_losses = 0        # Consecutive loss counter
        self.max_consecutive_losses = 2    # Trigger circuit breaker after 2 consecutive losses
        self.circuit_breaker_until = 0.0   # Timestamp until which trading is halted

    def record_trade_result(self, trade_result: Dict[str, Any]):
        """Records closed trade outcome to trigger circuit breakers or reset loss streaks."""
        self.last_trade_time = time.time()
        pnl = 0.0
        if isinstance(trade_result, dict):
            if "pnl_inr" in trade_result:
                pnl = float(trade_result.get("pnl_inr", 0.0))
            elif "trade" in trade_result and isinstance(trade_result["trade"], dict):
                pnl = float(trade_result["trade"].get("pnl_inr", 0.0))

        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"⚠️ [RISK ALERT] Loss recorded: ₹{pnl:+.2f} (Consecutive losses: {self.consecutive_losses})")
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.circuit_breaker_until = time.time() + 300.0  # 5-minute cooling off period
                logger.error(f"🛑 [CIRCUIT BREAKER TRIGGERED] {self.consecutive_losses} consecutive losses! Trading halted for 5 minutes.")
        else:
            if self.consecutive_losses > 0:
                logger.info(f"✅ Loss streak broken with profit: ₹{pnl:+.2f}. Streak reset to 0.")
            self.consecutive_losses = 0

    def evaluate_order(self, proposed_signal: Signal, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validates or vetoes a proposed trade signal. Enforces cooldowns, circuit breakers, and sizing."""
        if proposed_signal.action not in ["BUY", "SELL"]:
            return {"approved": False, "reason": "No actionable direction."}

        now = time.time()

        # 1. Circuit Breaker Check (Cooldown after loss streak)
        if now < self.circuit_breaker_until:
            remaining = int(self.circuit_breaker_until - now)
            return {
                "approved": False,
                "reason": f"Circuit breaker active ({remaining}s remaining). Halted to prevent drawdowns."
            }

        # 2. Overtrading Cooldown Check (Minimum interval between scalps)
        time_since_last = now - self.last_trade_time
        if self.last_trade_time > 0 and time_since_last < self.cooldown_sec:
            remaining = int(self.cooldown_sec - time_since_last)
            return {
                "approved": False,
                "reason": f"Overtrading cooldown active ({remaining}s remaining). Market digestion in progress."
            }

        # 3. Check if a position is already open (Strictly 1 position at a time)
        active_pos = state.get("active_position")
        if active_pos is not None:
            return {"approved": False, "reason": "Position already open. 100x multi-positioning is blocked."}

        # 4. Check Orderbook Spread
        ob = state.get("orderbook", {})
        spread_pct = ob.get("spread_pct", 999.0)
        if spread_pct > config.MAX_ALLOWABLE_SPREAD_PCT:
            return {
                "approved": False,
                "reason": f"Spread too wide ({spread_pct:.3f}% > max {config.MAX_ALLOWABLE_SPREAD_PCT:.3f}%). Slippage risk at 100x."
            }

        # 5. Dynamic Capital & Multi-Bullet Position Sizing
        balance_info = state.get("balance_info", {})
        available_margin_inr = balance_info.get("available_margin_inr") or balance_info.get("balance_inr", 50000.0)
        
        if available_margin_inr < 10.0:
            return {"approved": False, "reason": f"Insufficient margin reserve (₹{available_margin_inr:.2f} < ₹10.0)."}

        # Dynamic sizing: uses MARGIN_RATIO_PER_TRADE (10%) of actual available demo margin
        allocated_margin_inr = available_margin_inr * config.MARGIN_RATIO_PER_TRADE
        margin_usd = allocated_margin_inr / config.USD_INR_RATE
        notional_usd = margin_usd * config.LEVERAGE

        entry_price = proposed_signal.entry_price or (ob.get("best_bid") if proposed_signal.action == "BUY" else ob.get("best_ask"))
        if not entry_price or entry_price <= 0:
            return {"approved": False, "reason": "Invalid entry price."}

        # XRPUSD contract value = 1 XRP. Sized dynamically and capped safely
        contracts = int(notional_usd / entry_price)
        contracts = max(1, min(contracts, config.MAX_CONTRACTS_PER_TRADE))

        # 4. Bracket Levels (SL & TP)
        strategy_profile = state.get("strategy_profile", {})
        sl_pct = (strategy_profile.get("dynamic_sl_pct") or config.STOP_LOSS_PCT) / 100.0
        tp_pct = (strategy_profile.get("dynamic_tp_pct") or config.TAKE_PROFIT_PCT) / 100.0

        # Tick size is 0.0001 for XRPUSD
        tick_size = 0.0001
        def round_tick(val: float) -> float:
            return round(round(val / tick_size) * tick_size, 4)

        if proposed_signal.action == "BUY":
            sl_price = round_tick(entry_price * (1.0 - sl_pct))
            tp_price = round_tick(entry_price * (1.0 + tp_pct))
        else:
            sl_price = round_tick(entry_price * (1.0 + sl_pct))
            tp_price = round_tick(entry_price * (1.0 - tp_pct))

        actual_margin_inr = (contracts * entry_price * config.USD_INR_RATE) / config.LEVERAGE

        return {
            "approved": True,
            "action": proposed_signal.action,
            "contracts": contracts,
            "entry_price": round_tick(entry_price),
            "stop_loss": sl_price,
            "take_profit": tp_price,
            "margin_inr": round(actual_margin_inr, 2),
            "sl_distance_pct": round(sl_pct * 100, 2),
            "tp_distance_pct": round(tp_pct * 100, 2),
            "rationale": f"Approved {contracts} contracts (~₹{actual_margin_inr:.2f} margin at 100x). SL: ${sl_price} ({sl_pct*100:.2f}%), TP: ${tp_price} ({tp_pct*100:.2f}%)"
        }
