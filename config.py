"""
Configuration module for Delta Exchange Scalper Bot Swarm.
Supports:
1. DEMO / TESTNET: https://demo.delta.exchange (via https://testnet-api.delta.exchange)
2. PAPER: Local real-time simulation on live market data with virtual ₹100 INR.
3. LIVE: Real funds on Delta Exchange India (https://api.india.delta.exchange).
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Mode: 'demo' | 'paper' | 'live'
    MODE: str = os.getenv("BOT_MODE", "paper").lower()
    
    # Target Symbol (e.g. XRP, BTC, ETH, SOL)
    SYMBOL: str = os.getenv("SYMBOL", "XRP").upper()
    PRODUCT_ID: int = int(os.getenv("PRODUCT_ID", "0"))  # 0 = auto-detect
    
    # Delta API Credentials (needed for demo and live modes)
    API_KEY: str = os.getenv("DELTA_API_KEY", "")
    API_SECRET: str = os.getenv("DELTA_API_SECRET", "")
    
    # Groq LPU Quantitative AI Brain Configuration (Ultra-fast LLM inference)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    
    # Endpoints
    DEMO_WEB_URL: str = "https://demo.delta.exchange"
    DEMO_API_URL: str = os.getenv("DELTA_API_URL", "https://cdn-ind.testnet.deltaex.org")
    GLOBAL_TESTNET_URL: str = "https://testnet-api.delta.exchange"
    INDIA_LIVE_URL: str = "https://api.india.delta.exchange"
    
    # 100x Leverage Configuration
    LEVERAGE: int = int(os.getenv("LEVERAGE", "100"))
    
    # Capital & Sizing Parameters
    # Set to 0.0 to automatically use the full live balance from demo/live wallet
    INITIAL_CAPITAL_INR: float = float(os.getenv("INITIAL_CAPITAL_INR", "0.0"))
    USE_FULL_WALLET_BALANCE: bool = True
    USD_INR_RATE: float = float(os.getenv("USD_INR_RATE", "86.5"))
    
    # Fully Autonomous Execution
    AUTO_EXECUTION: bool = True
    AUTO_TAKE_PROFIT: bool = True
    TRAILING_STOP_ENABLED: bool = True
    
    # Capital & Margin Allocation: Unrestricted demo fund usage
    # 0.25 = 25% of available demo margin per bullet; can scale up to 1.0 (100% full demo fund)
    MARGIN_RATIO_PER_TRADE: float = float(os.getenv("MARGIN_RATIO_PER_TRADE", "0.25"))
    MAX_CONTRACTS_PER_TRADE: int = int(os.getenv("MAX_CONTRACTS_PER_TRADE", "100000"))
    MAX_OPEN_POSITIONS: int = 1
    
    # Scalping Stop-Loss & Take-Profit (% from entry)
    STOP_LOSS_PCT: float = 0.25   # 0.25% hard stop
    TAKE_PROFIT_PCT: float = 0.55  # 0.55% target profit (+55% return on margin at 100x)
    
    # Volatility and Spread filters (Testnet/Demo books have wider spreads than live)
    MAX_ALLOWABLE_SPREAD_PCT: float = float(os.getenv("MAX_ALLOWABLE_SPREAD_PCT", "2.5" if MODE in ["demo", "paper", "testnet"] else "0.15"))
    
    # Polling frequency in seconds
    POLL_INTERVAL_SEC: float = 2.0

    @property
    def base_url(self) -> str:
        if self.MODE == "live":
            return self.INDIA_LIVE_URL
        return self.DEMO_API_URL

config = Config()
