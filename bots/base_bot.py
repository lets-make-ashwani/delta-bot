"""
Base Agent Interface for Multi-Agent Swarm.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Signal:
    bot_name: str
    action: str  # "BUY" | "SELL" | "HOLD"
    confidence: float  # 0.0 to 1.0
    rationale: str
    entry_price: Optional[float] = None
    suggested_sl: Optional[float] = None
    suggested_tp: Optional[float] = None

class BaseBot:
    def __init__(self, name: str):
        self.name = name

    def analyze(self, state: Dict[str, Any]) -> Signal:
        raise NotImplementedError("Subclasses must implement analyze method.")
