"""
Multi-Agent Swarm Orchestrator (Full Quantitative Desk):
Coordinates communication, intelligence, and voting across all trading bots:
1. Market Analyst (Regime detection)
2. Strategy Generator (Dynamic SL/TP tuning)
3. Momentum Scalper (Breakout triggers)
4. Mean Reversion Scalper (Bollinger extremes)
5. Liquidity Wick Sweep (Stop-hunt reversals)
6. VWAP Sniper (Institutional pullback retests)
7. Order Book Wall Scalper (Microstructure depth defense)
8. RSI Divergence (Early exhaustion detection)
9. News & Sentiment Analyst (Crypto catalysts)
10. Jarvis AI Quantitative Brain ("Jev AI" multi-factor reasoning)
11. Chief Risk Officer (100x Multi-bullet veto & bracket calculation)
"""

import time
import logging
from typing import Dict, Any, Optional, List

from delta_client import DeltaExchangeManager
from indicators import calculate_indicators, calculate_orderbook_metrics
from bots.market_analyst import MarketAnalystBot
from bots.momentum_scalper import MomentumScalperBot
from bots.mean_reversion import MeanReversionBot
from bots.wick_sweep_scalper import WickSweepScalperBot
from bots.vwap_scalper import VwapScalperBot
from bots.orderbook_wall_scalper import OrderBookWallScalperBot
from bots.rsi_divergence import RsiDivergenceBot
from bots.strategy_generator import StrategyGeneratorBot
from bots.news_analyst import NewsAnalystBot
from bots.jarvis_ai import JarvisAIBot
from bots.risk_guardian import RiskGuardianBot
from bots.self_learning import swarm_learner
from bots.base_bot import Signal
from config import config

logger = logging.getLogger("SwarmOrchestrator")

class SwarmOrchestrator:
    def __init__(self):
        self.exchange = DeltaExchangeManager()
        self.learner = swarm_learner
        self.active_trade_context = {}
        
        # Instantiate Complete Bot Swarm Desk
        self.analyst = MarketAnalystBot()
        self.strategy_generator = StrategyGeneratorBot()
        
        # Specialized Execution Bots
        self.momentum_bot = MomentumScalperBot()
        self.mean_reversion_bot = MeanReversionBot()
        self.wick_sweep_bot = WickSweepScalperBot()
        self.vwap_bot = VwapScalperBot()
        self.ob_wall_bot = OrderBookWallScalperBot()
        self.rsi_div_bot = RsiDivergenceBot()
        
        # Intelligence & Risk Officers
        self.news_analyst = NewsAnalystBot()
        self.jarvis_ai = JarvisAIBot()
        self.risk_officer = RiskGuardianBot()
        
        self.last_candle_fetch = 0
        self.cached_candles = []
        self.cached_indicators = None
        self.iteration = 0
        self.latest_state = {}

    def tick(self) -> Dict[str, Any]:
        """Runs a single synchronization cycle across all bots in the swarm."""
        self.iteration += 1
        
        # 1. Fetch live quotes
        ticker_res = self.exchange.fetch_live_ticker()
        quotes = ticker_res.get("quotes", {})
        mark_price = float(ticker_res.get("mark_price") or ticker_res.get("close") or 0.0)
        ob_metrics = calculate_orderbook_metrics(quotes)

        # 2. Update existing position (check TP / SL / Liq)
        closed_trade = None
        if self.exchange.mode == "paper":
            closed_trade = self.exchange.paper.update_price(mark_price)

        # 3. Refresh 1-minute candles periodically (every 10 seconds)
        now = time.time()
        if now - self.last_candle_fetch > 10 or not self.cached_candles:
            self.cached_candles = self.exchange.fetch_candles(count=50, resolution="1m")
            if self.cached_candles:
                self.cached_indicators = calculate_indicators(self.cached_candles)
            self.last_candle_fetch = now

        # Active position & live balance
        active_position = self.exchange.get_active_position()
        balance_info = self.exchange.get_balance()

        # Shared swarm state
        state: Dict[str, Any] = {
            "symbol": self.exchange.symbol,
            "product_id": self.exchange.product_id,
            "contract_value": float(self.exchange.product.get("contract_value", 1.0)),
            "mark_price": mark_price,
            "orderbook": ob_metrics,
            "candles": self.cached_candles,
            "indicators": self.cached_indicators,
            "active_position": active_position,
            "balance_info": balance_info,
            "iteration": self.iteration,
            "mode": self.exchange.mode,
            "leverage": config.LEVERAGE
        }

        # Step 4: Run Market Analyst & News Analyst
        analyst_signal = self.analyst.analyze(state)
        news_signal = self.news_analyst.analyze(state)
        
        # Step 5: Run Strategy Generator (dynamic SL/TP tuning)
        strategy_signal = self.strategy_generator.analyze(state)
        strategy_profile = state.get("strategy_profile", {})

        # Step 6: Query ALL Strategy Bots
        mom_sig = self.momentum_bot.analyze(state)
        mr_sig = self.mean_reversion_bot.analyze(state)
        wick_sig = self.wick_sweep_bot.analyze(state)
        vwap_sig = self.vwap_bot.analyze(state)
        wall_sig = self.ob_wall_bot.analyze(state)
        div_sig = self.rsi_div_bot.analyze(state)

        # Step 7: Query Jarvis AI Quantitative Brain
        jarvis_sig = self.jarvis_ai.analyze(state)

        # Step 7.4: Dynamic Adaptive Bracket Tuning (Adjust SL & TP according to live analysis)
        adaptive_adjustments = []
        if active_position is not None:
            bracket_res = self.strategy_generator.tune_active_position_brackets(active_position, state)
            if bracket_res.get("updated"):
                adaptive_adjustments = bracket_res.get("adjustments", [])
                active_position["adaptive_adjustments"] = adaptive_adjustments
                logger.info(f"⚡ [ADAPTIVE BRACKETS] " + " | ".join(adaptive_adjustments))
                
                # Sync updated Stop-Loss to Delta Exchange server-side orders
                if bracket_res.get("new_sl") != bracket_res.get("old_sl") and self.exchange.mode in ["demo", "live"]:
                    self.exchange.update_stop_loss_order(
                        new_sl_price=bracket_res["new_sl"],
                        side=active_position["side"],
                        contracts=active_position["contracts"]
                    )

        # Step 7.5: Autonomous Active Position Management (TP, SL, Trailing, AI Reversal)
        closed_trade = None
        if active_position is not None and config.AUTO_EXECUTION:
            pos_side = active_position.get("side")
            tp_price = active_position.get("take_profit")
            sl_price = active_position.get("stop_loss")
            unrealized_pnl_inr = active_position.get("unrealized_pnl_inr", 0.0)
            
            # A. Check Take Profit Target Hit
            if (pos_side == "BUY" and tp_price and mark_price >= tp_price) or \
               (pos_side == "SELL" and tp_price and mark_price <= tp_price):
                logger.info(f"🎯 [AUTO TAKE-PROFIT] Target ${tp_price} reached at ${mark_price:.4f}! Booking profit...")
                closed_trade = self.exchange.close_position(reason="TAKE_PROFIT")
                active_position = None

            # B. Check Stop Loss Target Hit
            elif (pos_side == "BUY" and sl_price and mark_price <= sl_price) or \
                 (pos_side == "SELL" and sl_price and mark_price >= sl_price):
                logger.info(f"🛑 [AUTO STOP-LOSS] Level ${sl_price} breached at ${mark_price:.4f}! Cutting loss to protect capital...")
                closed_trade = self.exchange.close_position(reason="STOP_LOSS")
                active_position = None

            # C. Jarvis AI Strong Adverse Reversal Exit
            elif pos_side == "BUY" and jarvis_sig.action == "SELL" and jarvis_sig.confidence >= 0.82:
                logger.info(f"🧠 [AI EMERGENCY EXIT] Jarvis AI detected strong bearish reversal. Closing BUY scalp...")
                closed_trade = self.exchange.close_position(reason="AI_REVERSAL_EXIT")
                active_position = None
            elif pos_side == "SELL" and jarvis_sig.action == "BUY" and jarvis_sig.confidence >= 0.82:
                logger.info(f"🧠 [AI EMERGENCY EXIT] Jarvis AI detected strong bullish surge. Closing SELL scalp...")
                closed_trade = self.exchange.close_position(reason="AI_REVERSAL_EXIT")
                active_position = None

        if closed_trade:
            self.risk_officer.record_trade_result(closed_trade)
            self.learner.process_trade_outcome(closed_trade, self.active_trade_context)
            self.active_trade_context = {}

        # List of all active strategy signals
        all_signals = [mom_sig, mr_sig, wick_sig, vwap_sig, wall_sig, div_sig, jarvis_sig]

        # Step 8: Multi-Agent Consensus with Self-Learned Reinforcement Weights
        candidate_signal: Optional[Signal] = None

        # Each bot's vote confidence is scaled by its dynamic self-trained weight
        weighted_signals = []
        for s in all_signals:
            w = self.learner.get_bot_weight(s.bot_name)
            eff_conf = min(0.99, s.confidence * w)
            weighted_signals.append((s, eff_conf, w))

        # A. Check for High-Conviction Sniper Triggers (Effective Confidence >= 0.75)
        sniper_candidates = [item for item in weighted_signals if item[0].action in ["BUY", "SELL"] and item[1] >= 0.75]
        if sniper_candidates:
            # Pick highest effective confidence sniper
            best_sniper, best_eff_conf, best_w = max(sniper_candidates, key=lambda x: x[1])
            entry_price = ob_metrics.get("best_bid") if best_sniper.action == "BUY" else ob_metrics.get("best_ask")
            candidate_signal = Signal(
                bot_name=best_sniper.bot_name,
                action=best_sniper.action,
                confidence=best_eff_conf,
                rationale=f"[Learned Weight: {best_w:.2f}x] {best_sniper.rationale}",
                entry_price=entry_price
            )

        # B. Fallback: Self-Weighted Swarm Consensus
        if not candidate_signal:
            buy_votes = sum(eff_conf for s, eff_conf, w in weighted_signals if s.action == "BUY")
            sell_votes = sum(eff_conf for s, eff_conf, w in weighted_signals if s.action == "SELL")
            
            if buy_votes >= 1.25:
                candidate_signal = Signal(
                    bot_name="Self-Adaptive Swarm",
                    action="BUY",
                    confidence=min(0.95, buy_votes / 2.2),
                    rationale=f"Self-Adaptive Swarm BUY Consensus ({buy_votes:.2f} score across trained bots)",
                    entry_price=ob_metrics.get("best_bid")
                )
            elif sell_votes >= 1.25:
                candidate_signal = Signal(
                    bot_name="Self-Adaptive Swarm",
                    action="SELL",
                    confidence=min(0.95, sell_votes / 2.2),
                    rationale=f"Self-Adaptive Swarm SELL Consensus ({sell_votes:.2f} score across trained bots)",
                    entry_price=ob_metrics.get("best_ask")
                )

        # Step 9: Risk Evaluation & Execution
        execution_result = None
        risk_evaluation = None

        if candidate_signal and active_position is None and config.AUTO_EXECUTION:
            risk_evaluation = self.risk_officer.evaluate_order(candidate_signal, state)
            if risk_evaluation.get("approved"):
                execution_result = self.exchange.place_scalp_order(
                    side=risk_evaluation["action"],
                    contracts=risk_evaluation["contracts"],
                    entry_price=risk_evaluation["entry_price"],
                    sl_price=risk_evaluation["stop_loss"],
                    tp_price=risk_evaluation["take_profit"]
                )
                if execution_result and execution_result.get("success"):
                    self.risk_officer.last_trade_time = time.time()
                    self.active_trade_context = {
                        "regime": state.get("regime", "RANGING_CHOP"),
                        "trigger_bot": candidate_signal.bot_name,
                        "voting_records": {s.bot_name: s.action for s in all_signals}
                    }

        result_payload = {
            "state": state,
            "analyst_signal": analyst_signal,
            "news_signal": news_signal,
            "strategy_profile": strategy_profile,
            "mom_signal": mom_sig,
            "mr_signal": mr_sig,
            "wick_signal": wick_sig,
            "vwap_signal": vwap_sig,
            "wall_signal": wall_sig,
            "div_signal": div_sig,
            "jarvis_signal": jarvis_sig,
            "candidate_signal": candidate_signal,
            "risk_evaluation": risk_evaluation,
            "execution_result": execution_result,
            "closed_trade": closed_trade,
            "trade_metrics": self.exchange.get_trade_metrics(),
            "adaptive_adjustments": adaptive_adjustments,
            "self_learning": self.learner.get_dashboard_summary()
        }
        self.latest_state = result_payload
        return result_payload
