import time
import json
import logging
import requests
from typing import Dict, Any, Optional
from bots.base_bot import BaseBot, Signal
from config import config

logger = logging.getLogger("JarvisAI")

class JarvisAIBot(BaseBot):
    def __init__(self):
        super().__init__(name="Jarvis AI Quantitative Brain")
        self.last_groq_time = 0
        self.groq_cache: Optional[Dict[str, Any]] = None
        self.cache_duration_sec = 12.0  # Safe rate limit for Groq free tier (30 req/min)

    def _query_groq_lpu(self, symbol: str, mark_price: float, regime: str, rsi: float, ema_fast: float, ema_slow: float, imbalance: float, news_label: str, news_score: float) -> Optional[Dict[str, Any]]:
        """Invokes Groq LPU with Llama 3.3 70B for ultra-fast deep quantitative reasoning."""
        if not config.GROQ_API_KEY:
            return None

        now = time.time()
        if self.groq_cache and (now - self.last_groq_time < self.cache_duration_sec):
            return self.groq_cache

        try:
            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY.strip()}",
                "Content-Type": "application/json"
            }
            system_prompt = (
                "You are Jarvis AI, an elite 100x high-frequency quantitative hedge fund strategist for Delta Exchange. "
                "Analyze the technical microstructure and output strictly valid JSON with this exact schema:\n"
                "{\n"
                '  "verdict": "STRONG_BUY" | "LEAN_BUY" | "NEUTRAL_HOLD" | "LEAN_SELL" | "STRONG_SELL",\n'
                '  "quant_score": integer between -100 and 100,\n'
                '  "summary": "1 concise sentence with executive rationale"\n'
                "}"
            )
            user_prompt = (
                f"Instrument: {symbol} at ${mark_price:.4f}\n"
                f"Regime: {regime} | RSI: {rsi:.1f} | 9/21 EMA Trend: {'Bullish (9>21)' if ema_fast > ema_slow else 'Bearish (9<21)'}\n"
                f"Orderbook Depth Imbalance: {imbalance:+.2f} | News Catalyst: {news_label} (Score: {news_score:+.2f})\n"
                f"Deliver your executive quantitative verdict now."
            )
            payload = {
                "model": config.GROQ_MODEL,
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
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                self.groq_cache = parsed
                self.last_groq_time = now
                logger.info(f"⚡ [GROQ LPU REASONING] {parsed.get('verdict')} ({parsed.get('quant_score'):+d}/100): {parsed.get('summary')}")
                return parsed
            else:
                logger.debug(f"Groq API returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.debug(f"Groq LPU query notice: {e}")
        return None

    def analyze(self, state: Dict[str, Any]) -> Signal:
        indicators = state.get("indicators")
        ob = state.get("orderbook", {})
        news = state.get("news", {})
        regime = state.get("regime", "RANGING_CHOP")
        mark_price = state.get("mark_price", 0.0)
        symbol = state.get("symbol", "XRPUSD")

        if indicators is None or indicators.empty or not ob.get("valid"):
            return Signal(self.name, "HOLD", 0.0, "Synchronizing neural market feed...")

        latest = indicators.iloc[-1]
        rsi = latest["rsi"]
        ema_fast = latest["ema_fast"]
        ema_slow = latest["ema_slow"]
        imbalance = ob.get("imbalance", 0.0)
        spread_pct = ob.get("spread_pct", 0.0)
        sentiment_score = news.get("sentiment_score", 0.0)
        sentiment_label = news.get("sentiment_label", "NEUTRAL")

        # 1. Multi-factor Quantitative Scoring (-100 to +100)
        quant_score = 0
        reasons = []

        # Factor A: Trend & Momentum (+/- 30 pts)
        if ema_fast > ema_slow:
            quant_score += 25
            reasons.append("EMA fast > slow (Bullish)")
        else:
            quant_score -= 25
            reasons.append("EMA fast < slow (Bearish)")

        # Factor B: RSI Condition (+/- 25 pts)
        if rsi < 32:
            quant_score += 25
            reasons.append(f"RSI oversold at {rsi:.1f} (Bounce potential)")
        elif rsi > 68:
            quant_score -= 25
            reasons.append(f"RSI overbought at {rsi:.1f} (Rejection risk)")
        elif 52 <= rsi <= 64:
            quant_score += 15
            reasons.append(f"RSI bullish expansion at {rsi:.1f}")
        elif 36 <= rsi <= 48:
            quant_score -= 15
            reasons.append(f"RSI bearish drift at {rsi:.1f}")

        # Factor C: Orderbook Pressure (+/- 25 pts)
        if imbalance > 0.20:
            quant_score += 25
            reasons.append(f"Strong buyer book wall ({imbalance:+.2f})")
        elif imbalance < -0.20:
            quant_score -= 25
            reasons.append(f"Heavy seller ask wall ({imbalance:+.2f})")

        # Factor D: News Sentiment (+/- 20 pts)
        if sentiment_score >= 0.20:
            quant_score += int(sentiment_score * 20)
            reasons.append(f"Positive news catalyst ({sentiment_label})")
        elif sentiment_score <= -0.20:
            quant_score += int(sentiment_score * 20)  # negative
            reasons.append(f"Negative news headwind ({sentiment_label})")

        # 2. Executive AI Verdict
        if quant_score >= 50:
            verdict = "STRONG_BUY"
            action = "BUY"
            confidence = min(0.95, 0.65 + (quant_score / 200.0))
        elif quant_score >= 30:
            verdict = "LEAN_BUY"
            action = "BUY"
            confidence = 0.68
        elif quant_score <= -50:
            verdict = "STRONG_SELL"
            action = "SELL"
            confidence = min(0.95, 0.65 + (abs(quant_score) / 200.0))
        elif quant_score <= -30:
            verdict = "LEAN_SELL"
            action = "SELL"
            confidence = 0.68
        else:
            verdict = "NEUTRAL_HOLD"
            action = "HOLD"
            confidence = 0.50

        summary = f"[{verdict}] (Score: {quant_score:+d}/100) | " + "; ".join(reasons)
        powered_by = "Quant Matrix Engine"

        # 3. Enhance with Groq LPU LLM Inference if configured
        groq_res = self._query_groq_lpu(
            symbol=symbol,
            mark_price=mark_price,
            regime=regime,
            rsi=rsi,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            imbalance=imbalance,
            news_label=sentiment_label,
            news_score=sentiment_score
        )

        if groq_res:
            powered_by = f"Groq LPU ({config.GROQ_MODEL})"
            g_verdict = groq_res.get("verdict", verdict)
            if "BUY" in g_verdict:
                action = "BUY"
                confidence = 0.90 if "STRONG" in g_verdict else 0.75
                verdict = g_verdict
            elif "SELL" in g_verdict:
                action = "SELL"
                confidence = 0.90 if "STRONG" in g_verdict else 0.75
                verdict = g_verdict
            elif "HOLD" in g_verdict or "NEUTRAL" in g_verdict:
                action = "HOLD"
                confidence = 0.50
                verdict = "NEUTRAL_HOLD"

            if "quant_score" in groq_res:
                try:
                    quant_score = int(groq_res["quant_score"])
                except Exception:
                    pass

            if "summary" in groq_res:
                summary = f"[{verdict}] (Score: {quant_score:+d}/100) | {groq_res['summary']}"

        state["jarvis_ai"] = {
            "verdict": verdict,
            "quant_score": quant_score,
            "confidence": round(confidence * 100, 1),
            "reasons": reasons,
            "summary": summary,
            "powered_by": powered_by
        }

        entry_target = ob.get("best_bid") if action == "BUY" else ob.get("best_ask")

        return Signal(
            bot_name=self.name,
            action=action,
            confidence=confidence,
            rationale=summary,
            entry_price=entry_target
        )
