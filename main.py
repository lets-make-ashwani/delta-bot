"""
Main Execution Script for Delta Scalper Bot Swarm.
Supports:
    python main.py                     # Paper trading simulation on live XRP data (No API key needed)
    python main.py --mode demo         # Connects to https://demo.delta.exchange with Demo API keys
    python main.py --symbol BTC        # Trade Bitcoin instead of XRP
    python main.py --symbol ETH        # Trade Ethereum
    python main.py --symbol SOL        # Trade Solana
    python main.py --mode live         # Real trading on Delta India (₹100 real capital)
"""

import sys
import time
import argparse
import logging

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import config
from orchestrator import SwarmOrchestrator
from dashboard import render_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("bot_swarm.log", encoding="utf-8")
    ]
)

def parse_args():
    parser = argparse.ArgumentParser(description="Delta Exchange 100x Scalper Swarm")
    parser.add_argument("--mode", choices=["demo", "paper", "testnet", "live"], default="paper",
                        help="Mode: 'demo' (https://demo.delta.exchange), 'paper' (simulated live), or 'live'")
    parser.add_argument("--symbol", type=str, default="XRP",
                        help="Target crypto symbol (e.g. XRP, BTC, ETH, SOL)")
    parser.add_argument("--capital", type=float, default=100.0,
                        help="Initial capital in INR (default: 100.0)")
    parser.add_argument("--leverage", type=int, default=100,
                        help="Leverage multiplier (default: 100)")
    return parser.parse_args()

def main():
    args = parse_args()
    config.MODE = "demo" if args.mode in ["demo", "testnet"] else args.mode
    config.SYMBOL = args.symbol.upper()
    config.INITIAL_CAPITAL_INR = args.capital
    config.LEVERAGE = args.leverage

    print(f"\n🚀 Initializing Delta Exchange Swarm in [{config.MODE.upper()}] mode...")
    print(f"💎 Target: {config.SYMBOL} | Leverage: {config.LEVERAGE}x | Capital: INR {config.INITIAL_CAPITAL_INR:.2f}")
    if config.MODE == "demo":
        print(f"🌐 Connected to Demo Web Platform: {config.DEMO_WEB_URL}")

    orchestrator = SwarmOrchestrator()
    print(f"✅ Bot Swarm online for [{orchestrator.exchange.symbol}] (Product ID: {orchestrator.exchange.product_id})")
    print("Press Ctrl+C at any time to pause or exit.\n")

    try:
        while True:
            tick_data = orchestrator.tick()
            render_dashboard(tick_data)
            time.sleep(config.POLL_INTERVAL_SEC)
    except KeyboardInterrupt:
        print("\n🛑 Swarm loop paused by user.")
        bal = orchestrator.exchange.get_balance()
        print(f"Final Account Balance: INR {bal.get('balance_inr', 0):.2f}")
        sys.exit(0)

if __name__ == "__main__":
    main()
