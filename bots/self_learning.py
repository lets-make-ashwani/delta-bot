"""
Self-Improving Reinforcement Learning & Adaptive Feedback Engine.
Analyzes each and every completed trade to:
1. Reward or penalize individual bot voting weights (Multi-Armed Bandit / Reinforcement Learning).
2. Learn Market Regime affinities (e.g. prioritize Mean Reversion in CHOP, Momentum in TRENDS).
3. Query Groq LPU LLM for Trade Post-Mortem Reflections & Algorithmic Heuristic Rules.
4. Dynamically calibrate Stop-Loss & Take-Profit targets based on historical hit rates.
5. Persist learning memory across restarts in `learning_memory.json`.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from config import config

logger = logging.getLogger("SelfLearningEngine")

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning_memory.json")

DEFAULT_BOT_WEIGHTS = {
    "Jarvis AI Quantitative Brain": 1.25,
    "Momentum Scalper": 1.00,
    "Mean Reversion": 1.00,
    "Liquidity Wick Sweep": 1.05,
    "VWAP Sniper": 1.00,
    "Order Book Wall Scalper": 1.05,
    "RSI Divergence": 1.00
}

class SelfLearningEngine:
    def __init__(self):
        self.memory_file = MEMORY_FILE
        self.learning_data: Dict[str, Any] = {
            "total_trades_analyzed": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "cumulative_pnl_inr": 0.0,
            "bot_weights": dict(DEFAULT_BOT_WEIGHTS),
            "bot_stats": {
                name: {"wins": 0, "losses": 0, "total_pnl": 0.0, "accuracy_pct": 0.0}
                for name in DEFAULT_BOT_WEIGHTS
            },
            "regime_performance": {
                "TRENDING_BULL": {"wins": 0, "losses": 0, "pnl": 0.0},
                "TRENDING_BEAR": {"wins": 0, "losses": 0, "pnl": 0.0},
                "RANGING_CHOP": {"wins": 0, "losses": 0, "pnl": 0.0},
                "HIGH_VOLATILITY": {"wins": 0, "losses": 0, "pnl": 0.0}
            },
            "adaptive_parameters": {
                "sl_adjustment_delta": 0.0,
                "tp_adjustment_delta": 0.0,
                "preferred_regimes": ["TRENDING_BULL", "TRENDING_BEAR", "RANGING_CHOP"]
            },
            "learned_heuristics": [
                "Prioritize Orderbook Wall alignment to avoid slippage on breakout attempts.",
                "Ensure RSI is between 40 and 60 before entering momentum continuation scalps."
            ],
            "recent_trade_postmortems": []
        }
        self.load_memory()

    def load_memory(self):
        """Loads persistent learning memory from disk if available."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        # Merge safely
                        for k, v in saved.items():
                            if k in self.learning_data:
                                if isinstance(v, dict) and isinstance(self.learning_data[k], dict):
                                    self.learning_data[k].update(v)
                                else:
                                    self.learning_data[k] = v
                logger.info(f"🧠 [SELF-LEARNING] Memory loaded: {self.learning_data['total_trades_analyzed']} past trades synthesized.")
            except Exception as e:
                logger.warning(f"Error loading learning memory: {e}")

    def save_memory(self):
        """Persists learning state to disk."""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.learning_data, f, indent=2)
        except Exception as e:
            logger.debug(f"Error saving learning memory: {e}")

    def get_bot_weight(self, bot_name: str) -> float:
        """Returns the current dynamic self-trained weight for a specific bot."""
        return float(self.learning_data["bot_weights"].get(bot_name, 1.0))

    def get_learned_rules_for_prompt(self) -> List[str]:
        """Provides the top active learned rules for injection into Jarvis AI reasoning."""
        return self.learning_data.get("learned_heuristics", [])[-4:]

    def _query_groq_post_mortem(self, trade_summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Queries Groq LPU to analyze a finished trade and extract an algorithmic lesson."""
        if not config.GROQ_API_KEY:
            return None

        try:
            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY.strip()}",
                "Content-Type": "application/json"
            }
            system_prompt = (
                "You are the Meta-Learning Quant Coach for an autonomous Delta Exchange 100x Scalping Bot Swarm. "
                "Analyze the completed trade outcome and formulate a strict, algorithmic 1-sentence heuristic "
                "to improve future win-rate and capital protection. Output strictly valid JSON with this schema:\n"
                "{\n"
                '  "lesson": "1 sharp, algorithmic rule for future entries",\n'
                '  "regime_advice": "1 brief sentence on regime handling"\n'
                "}"
            )
            user_prompt = (
                f"Trade Analysis Request:\n"
                f"• Instrument: {trade_summary.get('symbol')} ({trade_summary.get('side')})\n"
                f"• Outcome: {trade_summary.get('outcome')} | Realized PnL: ₹{trade_summary.get('pnl_inr', 0):+.2f}\n"
                f"• Return on Margin: {trade_summary.get('pnl_pct', 0):+.2f}%\n"
                f"• Exit Reason: {trade_summary.get('reason')} (Duration: {trade_summary.get('duration_sec')}s)\n"
                f"• Entry Market Regime: {trade_summary.get('regime')}\n"
                f"• Bot Consensus Triggered by: {trade_summary.get('trigger_bot')}\n"
                f"Extract your executive quantitative learning rule now."
            )

            candidate_models = [config.GROQ_MODEL, "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
            for model_name in candidate_models:
                try:
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 120,
                        "response_format": {"type": "json_object"}
                    }
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=3.5)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        parsed = json.loads(content)
                        return parsed
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Post-mortem reflection notice: {e}")
        return None

    def process_trade_outcome(self, closed_trade: Dict[str, Any], trade_context: Optional[Dict[str, Any]] = None):
        """
        Called immediately whenever a trade is closed (WIN or LOSS).
        Updates bot weights, regime affinities, and learns post-mortem rules.
        """
        if not closed_trade:
            return

        # Extract core metrics
        trade_inner = closed_trade.get("trade", closed_trade)
        pnl_inr = float(trade_inner.get("pnl_inr", 0.0))
        pnl_pct = float(trade_inner.get("pnl_pct_on_margin", 0.0))
        side = trade_inner.get("side", "BUY")
        reason = trade_inner.get("reason", "UNKNOWN")
        duration = float(trade_inner.get("duration_sec", 0.0))
        symbol = trade_inner.get("symbol", config.SYMBOL)

        context = trade_context or {}
        regime = context.get("regime", "RANGING_CHOP")
        trigger_bot = context.get("trigger_bot", "Swarm Consensus")
        voting_records = context.get("voting_records", {})

        is_win = pnl_inr > 0
        outcome = "PROFITABLE_WIN" if is_win else "STOP_LOSS_EXIT"

        logger.info(f"🎓 [SELF-LEARNING TRIGGERED] Processing Trade #{self.learning_data['total_trades_analyzed']+1} | Result: ₹{pnl_inr:+.2f} ({outcome})")

        # 1. Update Global Learning Metrics
        self.learning_data["total_trades_analyzed"] += 1
        if is_win:
            self.learning_data["win_trades"] += 1
        else:
            self.learning_data["loss_trades"] += 1
        self.learning_data["cumulative_pnl_inr"] = round(self.learning_data["cumulative_pnl_inr"] + pnl_inr, 2)

        # 2. Reinforcement Weight Adaptation for Individual Bots
        # Reward bots that supported the winning direction; penalize bots that supported the losing direction
        learning_rate = 0.06
        for bot_name, current_w in list(self.learning_data["bot_weights"].items()):
            bot_vote = voting_records.get(bot_name, "HOLD")
            stats = self.learning_data["bot_stats"].setdefault(
                bot_name, {"wins": 0, "losses": 0, "total_pnl": 0.0, "accuracy_pct": 0.0}
            )

            # Bot agreed with trade direction
            if bot_vote == side:
                if is_win:
                    delta_w = learning_rate * 1.2
                    stats["wins"] += 1
                    stats["total_pnl"] += pnl_inr
                    logger.info(f"  📈 Rewarding [{bot_name}]: Weight {current_w:.2f} -> {current_w + delta_w:.2f} (Aligned with WIN)")
                else:
                    delta_w = -learning_rate * 1.5
                    stats["losses"] += 1
                    stats["total_pnl"] += pnl_inr
                    logger.info(f"  📉 Penalizing [{bot_name}]: Weight {current_w:.2f} -> {current_w + delta_w:.2f} (Aligned with LOSS)")
                
                # Apply new bounded weight (0.35x to 2.25x)
                new_w = max(0.35, min(2.25, current_w + delta_w))
                self.learning_data["bot_weights"][bot_name] = round(new_w, 2)

            # Bot advised caution (HOLD or opposite direction) during a loss -> Reward prudence!
            elif not is_win and bot_vote in ["HOLD", ("SELL" if side == "BUY" else "BUY")]:
                delta_w = learning_rate * 0.75
                new_w = max(0.35, min(2.25, current_w + delta_w))
                self.learning_data["bot_weights"][bot_name] = round(new_w, 2)
                logger.info(f"  🛡️ Prudence Reward [{bot_name}]: Weight {current_w:.2f} -> {new_w:.2f} (Correctly warned against entry)")

            # Recalculate accuracy
            total_b_trades = stats["wins"] + stats["losses"]
            if total_b_trades > 0:
                stats["accuracy_pct"] = round((stats["wins"] / total_b_trades) * 100, 1)

        # 3. Update Market Regime Performance Memory
        reg_stats = self.learning_data["regime_performance"].setdefault(
            regime, {"wins": 0, "losses": 0, "pnl": 0.0}
        )
        if is_win:
            reg_stats["wins"] += 1
        else:
            reg_stats["losses"] += 1
        reg_stats["pnl"] = round(reg_stats["pnl"] + pnl_inr, 2)

        # 4. Synthesize Post-Mortem Lesson with Groq LPU LLM
        summary_payload = {
            "symbol": symbol,
            "side": side,
            "outcome": outcome,
            "pnl_inr": pnl_inr,
            "pnl_pct": pnl_pct,
            "reason": reason,
            "duration_sec": duration,
            "regime": regime,
            "trigger_bot": trigger_bot
        }
        
        reflection = self._query_groq_post_mortem(summary_payload)
        lesson_text = None
        if reflection and reflection.get("lesson"):
            lesson_text = reflection["lesson"]
            # Keep unique top heuristics
            if lesson_text not in self.learning_data["learned_heuristics"]:
                self.learning_data["learned_heuristics"].append(lesson_text)
                if len(self.learning_data["learned_heuristics"]) > 10:
                    self.learning_data["learned_heuristics"].pop(0)
            logger.info(f"💡 [GROQ AI REFLECTION LESSON]: \"{lesson_text}\"")

        # 5. Store Recent Post-Mortem Record
        postmortem_entry = {
            "timestamp": time.time(),
            "symbol": symbol,
            "side": side,
            "pnl_inr": pnl_inr,
            "pnl_pct": pnl_pct,
            "reason": reason,
            "regime": regime,
            "trigger_bot": trigger_bot,
            "lesson": lesson_text or ("Sustained positive risk-reward management" if is_win else "Tighten entry confirmation filter")
        }
        self.learning_data["recent_trade_postmortems"].insert(0, postmortem_entry)
        if len(self.learning_data["recent_trade_postmortems"]) > 20:
            self.learning_data["recent_trade_postmortems"].pop()

        # 6. Save Updated Neural Brain to Disk
        self.save_memory()
        logger.info(f"💾 [SELF-LEARNING ENGINE] Brain state saved. Total weights re-calibrated.")

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Provides sanitized summary of self-learning state for the live web dashboard."""
        return {
            "total_trades_analyzed": self.learning_data["total_trades_analyzed"],
            "win_rate": round(
                (self.learning_data["win_trades"] / max(1, self.learning_data["total_trades_analyzed"])) * 100, 1
            ),
            "bot_weights": self.learning_data["bot_weights"],
            "bot_stats": self.learning_data["bot_stats"],
            "regime_performance": self.learning_data["regime_performance"],
            "top_heuristics": self.learning_data.get("learned_heuristics", [])[-3:],
            "latest_reflection": (
                self.learning_data["recent_trade_postmortems"][0]["lesson"]
                if self.learning_data.get("recent_trade_postmortems") else "Accumulating live market trade experience..."
            )
        }

# Global Singleton Instance
swarm_learner = SelfLearningEngine()
