"""
Multi-Agent Swarm Orchestrator (Full Quantitative Desk with Multi-Asset Radar):
Coordinates communication, intelligence, and voting across all trading bots:
1. Multi-Asset Radar: Continuously scans and analyzes BTC, ETH, SOL, and XRP simultaneously.
2. Market Analyst (Regime detection per coin)
3. Strategy Generator (Dynamic SL/TP tuning)
4. Momentum Scalper (Breakout triggers)
5. Mean Reversion Scalper (Bollinger extremes)
6. Liquidity Wick Sweep (Stop-hunt reversals)
7. VWAP Sniper (Institutional pullback retests)
8. Order Book Wall Scalper (Microstructure depth defense)
9. RSI Divergence (Early exhaustion detection)
10. News & Sentiment Analyst (Crypto catalysts)
11. Jarvis AI Quantitative Brain ("Jev AI" multi-factor reasoning)
12. Chief Risk Officer (100x Multi-bullet veto & bracket calculation)
"""

import time
import logging
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

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

SUPPORTED_SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

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
        
        # Per-symbol candle and indicator cache (10s refresh)
        self.candles_cache: Dict[str, Dict[str, Any]] = {}
        self.iteration = 0
        self.latest_state = {}

    def _get_symbol_candles_and_indicators(self, symbol: str) -> tuple:
        """Fetches and caches 1-minute historical candles and indicators for any symbol."""
        now = time.time()
        cached = self.candles_cache.get(symbol)
        if cached and (now - cached.get("last_fetch", 0) < 10) and cached.get("indicators") is not None:
            return cached.get("candles", []), cached.get("indicators")

        candles = self.exchange.fetch_candles(count=50, resolution="1m", symbol=symbol)
        indicators = calculate_indicators(candles) if candles else None
        self.candles_cache[symbol] = {
            "last_fetch": now,
            "candles": candles,
            "indicators": indicators
        }
        return candles, indicators

    def evaluate_symbol_signals(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the entire quantitative swarm across an individual asset's state."""
        # Step 1: Market Analyst (regime)
        analyst_signal = self.analyst.analyze(state)
        
        # Step 2: News Analyst
        news_signal = self.news_analyst.analyze(state)
        
        # Step 3: Strategy Generator (dynamic SL/TP)
        strategy_signal = self.strategy_generator.analyze(state)
        strategy_profile = state.get("strategy_profile", {})

        # Step 4: Specialized Execution Bots
        mom_sig = self.momentum_bot.analyze(state)
        mr_sig = self.mean_reversion_bot.analyze(state)
        wick_sig = self.wick_sweep_bot.analyze(state)
        vwap_sig = self.vwap_bot.analyze(state)
        wall_sig = self.ob_wall_bot.analyze(state)
        div_sig = self.rsi_div_bot.analyze(state)

        # Step 5: Jarvis AI Quantitative Brain
        jarvis_sig = self.jarvis_ai.analyze(state)

        all_signals = [mom_sig, mr_sig, wick_sig, vwap_sig, wall_sig, div_sig, jarvis_sig]

        # Step 6: Multi-Agent Consensus with Self-Learned Reinforcement Weights
        candidate_signal: Optional[Signal] = None
        ob_metrics = state.get("orderbook", {})

        weighted_signals = []
        for s in all_signals:
            w = self.learner.get_bot_weight(s.bot_name)
            eff_conf = min(0.99, s.confidence * w)
            weighted_signals.append((s, eff_conf, w))

        # Sniper Triggers (Effective Confidence >= 0.75)
        sniper_candidates = [item for item in weighted_signals if item[0].action in ["BUY", "SELL"] and item[1] >= 0.75]
        if sniper_candidates:
            best_sniper, best_eff_conf, best_w = max(sniper_candidates, key=lambda x: x[1])
            entry_price = ob_metrics.get("best_bid") if best_sniper.action == "BUY" else ob_metrics.get("best_ask")
            candidate_signal = Signal(
                bot_name=best_sniper.bot_name,
                action=best_sniper.action,
                confidence=best_eff_conf,
                rationale=f"[Learned Weight: {best_w:.2f}x] {best_sniper.rationale}",
                entry_price=entry_price
            )

        # Fallback: Swarm Consensus
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

        return {
            "analyst_signal": analyst_signal,
            "news_signal": news_signal,
            "strategy_profile": strategy_profile,
            "all_signals": all_signals,
            "mom_signal": mom_sig,
            "mr_signal": mr_sig,
            "wick_signal": wick_sig,
            "vwap_signal": vwap_sig,
            "wall_signal": wall_sig,
            "div_signal": div_sig,
            "jarvis_signal": jarvis_sig,
            "candidate_signal": candidate_signal
        }

    def scan_coin(self, coin: str, balance_info: Dict[str, float]) -> Dict[str, Any]:
        """Analyzes a single crypto asset across all strategies and microstructure metrics."""
        prod = self.exchange._resolve_product(coin, self.exchange.target_url)
        sym = prod.get("symbol", f"{coin}USD")
        
        ticker_res = self.exchange.fetch_live_ticker(sym)
        quotes = ticker_res.get("quotes", {})
        mark_price = float(ticker_res.get("mark_price") or ticker_res.get("close") or 0.0)
        ob_metrics = calculate_orderbook_metrics(quotes)
        
        candles, indicators = self._get_symbol_candles_and_indicators(coin)
        
        coin_state: Dict[str, Any] = {
            "symbol": sym,
            "product_id": prod.get("id"),
            "contract_value": float(prod.get("contract_value", 1.0)),
            "tick_size": float(prod.get("tick_size", 0.0001)),
            "mark_price": mark_price,
            "orderbook": ob_metrics,
            "candles": candles,
            "indicators": indicators,
            "active_position": None,
            "balance_info": balance_info,
            "iteration": self.iteration,
            "mode": self.exchange.mode,
            "leverage": config.LEVERAGE
        }

        eval_res = self.evaluate_symbol_signals(coin_state)
        candidate = eval_res.get("candidate_signal")
        jarvis_info = coin_state.get("jarvis_ai", {})
        
        # Calculate Opportunity Score for Ranking
        opp_score = 0.0
        if candidate and candidate.action in ["BUY", "SELL"]:
            opp_score = candidate.confidence
            j_score = jarvis_info.get("quant_score", 0)
            if (candidate.action == "BUY" and j_score > 20) or (candidate.action == "SELL" and j_score < -20):
                opp_score += 0.15  # Bonus for AI confirmation
        
        return {
            "base_coin": coin,
            "symbol": sym,
            "product_id": prod.get("id"),
            "mark_price": mark_price,
            "spread_pct": ob_metrics.get("spread_pct", 0.0),
            "imbalance": ob_metrics.get("imbalance", 0.0),
            "regime": coin_state.get("regime", "RANGING_CHOP"),
            "action": candidate.action if candidate else "HOLD",
            "confidence": round(candidate.confidence, 2) if candidate else 0.50,
            "trigger_bot": candidate.bot_name if candidate else "Radar Scanning",
            "rationale": candidate.rationale if candidate else "No high-conviction breakout",
            "jarvis_score": jarvis_info.get("quant_score", 0),
            "jarvis_verdict": jarvis_info.get("verdict", "NEUTRAL_HOLD"),
            "opp_score": round(opp_score, 3),
            "state": coin_state,
            "eval_res": eval_res
        }

    def tick(self) -> Dict[str, Any]:
        """Runs a complete multi-asset synchronization cycle across BTC, ETH, SOL, and XRP."""
        self.iteration += 1
        
        balance_info = self.exchange.get_balance()
        active_position = self.exchange.get_active_position()

        # Step 1: Scan all 4 assets concurrently for maximum responsiveness
        radar_results: Dict[str, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_coin = {executor.submit(self.scan_coin, coin, balance_info): coin for coin in SUPPORTED_SYMBOLS}
            for future in future_to_coin:
                coin = future_to_coin[future]
                try:
                    radar_results[coin] = future.result()
                except Exception as e:
                    logger.debug(f"Error scanning {coin}: {e}")

        # Step 2: Rank the opportunities across all 4 coins
        # Sort by opportunity score descending
        sorted_opps = sorted(radar_results.values(), key=lambda x: x["opp_score"], reverse=True)
        top_pick = sorted_opps[0] if sorted_opps else None
        top_coin = top_pick["base_coin"] if top_pick else self.exchange.symbol

        # Step 3: Determine Active Focus Coin
        # If an active position exists, stay locked onto the active position's symbol!
        if active_position is not None:
            active_sym = active_position.get("symbol", self.exchange.symbol)
            focus_coin = next((c for c in SUPPORTED_SYMBOLS if c in active_sym), "XRP")
        else:
            # If no open trade and a strong setup exists, target the top pick!
            if top_pick and top_pick["opp_score"] >= 0.70:
                focus_coin = top_coin
            else:
                focus_coin = next((c for c in SUPPORTED_SYMBOLS if c in self.exchange.symbol), "XRP")

        focus_data = radar_results.get(focus_coin, sorted_opps[0] if sorted_opps else {})
        focus_state = focus_data.get("state", {})
        focus_eval = focus_data.get("eval_res", {})
        focus_candidate = focus_eval.get("candidate_signal")
        mark_price = focus_data.get("mark_price", 0.0)

        # Update active position in state
        focus_state["active_position"] = active_position
        focus_state["balance_info"] = balance_info

        # Step 4: Dynamic Adaptive Bracket Tuning for Active Position
        adaptive_adjustments = []
        if active_position is not None:
            bracket_res = self.strategy_generator.tune_active_position_brackets(active_position, focus_state)
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

        # Step 5: Autonomous Active Position Management (TP, SL, Trailing, AI Reversal)
        closed_trade = None
        if active_position is not None and config.AUTO_EXECUTION:
            pos_side = active_position.get("side")
            tp_price = active_position.get("take_profit")
            sl_price = active_position.get("stop_loss")
            jarvis_sig = focus_eval.get("jarvis_signal")
            
            # Check Take Profit Target Hit
            if (pos_side == "BUY" and tp_price and mark_price >= tp_price) or \
               (pos_side == "SELL" and tp_price and mark_price <= tp_price):
                logger.info(f"🎯 [AUTO TAKE-PROFIT] Target ${tp_price} reached at ${mark_price:.4f}! Booking profit on {focus_coin}...")
                closed_trade = self.exchange.close_position(reason="TAKE_PROFIT")
                active_position = None

            # Check Stop Loss Target Hit
            elif (pos_side == "BUY" and sl_price and mark_price <= sl_price) or \
                 (pos_side == "SELL" and sl_price and mark_price >= sl_price):
                logger.info(f"🛑 [AUTO STOP-LOSS] Level ${sl_price} breached at ${mark_price:.4f}! Cutting loss on {focus_coin}...")
                closed_trade = self.exchange.close_position(reason="STOP_LOSS")
                active_position = None

            # Jarvis AI Strong Adverse Reversal Exit
            elif jarvis_sig and pos_side == "BUY" and jarvis_sig.action == "SELL" and jarvis_sig.confidence >= 0.82:
                logger.info(f"🧠 [AI EMERGENCY EXIT] Jarvis AI detected strong bearish reversal. Closing BUY scalp on {focus_coin}...")
                closed_trade = self.exchange.close_position(reason="AI_REVERSAL_EXIT")
                active_position = None
            elif jarvis_sig and pos_side == "SELL" and jarvis_sig.action == "BUY" and jarvis_sig.confidence >= 0.82:
                logger.info(f"🧠 [AI EMERGENCY EXIT] Jarvis AI detected strong bullish surge. Closing SELL scalp on {focus_coin}...")
                closed_trade = self.exchange.close_position(reason="AI_REVERSAL_EXIT")
                active_position = None

        if closed_trade:
            self.risk_officer.record_trade_result(closed_trade)
            self.learner.process_trade_outcome(closed_trade, self.active_trade_context)
            self.active_trade_context = {}

        # Step 6: Autonomous Trade Execution on Best Opportunity
        execution_result = None
        risk_evaluation = None

        if active_position is None and config.AUTO_EXECUTION and top_pick and top_pick["opp_score"] >= 0.70:
            top_candidate = top_pick["eval_res"].get("candidate_signal")
            top_state = top_pick["state"]
            
            if top_candidate and top_candidate.action in ["BUY", "SELL"]:
                # Switch active trading symbol on exchange to the winning coin
                if self.exchange.symbol != top_pick["symbol"]:
                    self.exchange.switch_symbol(top_pick["base_coin"])
                
                risk_evaluation = self.risk_officer.evaluate_order(top_candidate, top_state)
                if risk_evaluation.get("approved"):
                    logger.info(f"🚀 [MULTI-ASSET OPPORTUNITY TRIGGERED] Selecting {top_pick['base_coin']} (Opp Score: {top_pick['opp_score']:.2f}) among [BTC, ETH, SOL, XRP]!")
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
                            "regime": top_state.get("regime", "RANGING_CHOP"),
                            "trigger_bot": top_candidate.bot_name,
                            "symbol": top_pick["base_coin"],
                            "voting_records": {s.bot_name: s.action for s in top_pick["eval_res"].get("all_signals", [])}
                        }

        # Build clean Multi-Asset Radar payload for dashboard
        clean_radar = {}
        for coin, r in radar_results.items():
            clean_radar[coin] = {
                "base_coin": coin,
                "symbol": r["symbol"],
                "mark_price": r["mark_price"],
                "spread_pct": r["spread_pct"],
                "imbalance": r["imbalance"],
                "regime": r["regime"],
                "action": r["action"],
                "confidence": r["confidence"],
                "trigger_bot": r["trigger_bot"],
                "rationale": r["rationale"],
                "jarvis_score": r["jarvis_score"],
                "jarvis_verdict": r["jarvis_verdict"],
                "opp_score": r["opp_score"],
                "is_active": (coin == focus_coin),
                "is_top_pick": (coin == top_coin and top_pick and top_pick["opp_score"] >= 0.70)
            }

        result_payload = {
            "state": focus_state,
            "analyst_signal": focus_eval.get("analyst_signal"),
            "news_signal": focus_eval.get("news_signal"),
            "strategy_profile": focus_eval.get("strategy_profile"),
            "mom_signal": focus_eval.get("mom_signal"),
            "mr_signal": focus_eval.get("mr_signal"),
            "wick_signal": focus_eval.get("wick_signal"),
            "vwap_signal": focus_eval.get("vwap_signal"),
            "wall_signal": focus_eval.get("wall_signal"),
            "div_signal": focus_eval.get("div_signal"),
            "jarvis_signal": focus_eval.get("jarvis_signal"),
            "candidate_signal": focus_candidate,
            "risk_evaluation": risk_evaluation,
            "execution_result": execution_result,
            "closed_trade": closed_trade,
            "trade_metrics": self.exchange.get_trade_metrics(),
            "adaptive_adjustments": adaptive_adjustments,
            "self_learning": self.learner.get_dashboard_summary(),
            "multi_asset_radar": clean_radar,
            "top_opportunity": {
                "coin": top_coin,
                "opp_score": top_pick["opp_score"] if top_pick else 0.0,
                "action": top_pick["action"] if top_pick else "HOLD",
                "trigger_bot": top_pick["trigger_bot"] if top_pick else "None"
            } if top_pick else None
        }
        self.latest_state = result_payload
        return result_payload
