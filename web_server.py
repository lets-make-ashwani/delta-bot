"""
Web Dashboard Server for Delta Quant Swarm.
Hosts a real-time web application monitoring the multi-agent bot swarm,
live market ticks, news sentiment, and Jarvis AI ("Jev AI") quantitative decisions.
"""

import os
import sys
import time
import threading
import logging
from flask import Flask, render_template, jsonify, request
from config import config
from orchestrator import SwarmOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DashboardServer")

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "web", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "web", "static")
)

# Global orchestrator instance
orchestrator = None
latest_data = {}
is_running = True
worker_thread_started = False

def background_swarm_worker():
    """Continuously runs the SwarmOrchestrator loop in the background."""
    global orchestrator, latest_data, is_running
    logger.info("Starting background Swarm worker thread...")
    while is_running:
        try:
            if orchestrator:
                tick_result = orchestrator.tick()
                latest_data = tick_result
        except Exception as e:
            logger.error(f"Error in swarm tick loop: {e}")
        time.sleep(config.POLL_INTERVAL_SEC)

@app.route("/")
def index():
    """Serves the main web dashboard."""
    return render_template("index.html")

def sanitize_val(v):
    """Recursively converts pandas Series, DataFrames, numpy types, and Signals to JSON-safe structures."""
    try:
        import pandas as pd
        import numpy as np
        from bots.base_bot import Signal

        if isinstance(v, pd.Series):
            return v.to_dict()
        if isinstance(v, pd.DataFrame):
            return v.to_dict('records')
        if isinstance(v, (np.integer, np.floating)):
            return v.item()
        if isinstance(v, Signal):
            return {
                "bot_name": v.bot_name,
                "action": v.action,
                "confidence": float(v.confidence),
                "rationale": v.rationale,
                "entry_price": v.entry_price
            }
    except Exception:
        pass

    if isinstance(v, dict):
        return {k: sanitize_val(val) for k, val in v.items() if k not in ["indicators", "candles"]}
    if isinstance(v, list):
        return [sanitize_val(item) for item in v]
    return v

def get_orchestrator():
    global orchestrator, worker_thread_started
    if orchestrator is None:
        orchestrator = SwarmOrchestrator()
    if not worker_thread_started:
        worker_thread = threading.Thread(target=background_swarm_worker, daemon=True)
        worker_thread.start()
        worker_thread_started = True
    return orchestrator

@app.route("/api/status")
def get_status():
    """Returns the latest multi-agent state as JSON."""
    global latest_data
    orch = get_orchestrator()
    if not latest_data:
        try:
            latest_data = orch.tick()
        except Exception as e:
            logger.error(f"Error ticking orchestrator: {e}")
            latest_data = {}
    
    clean_data = sanitize_val(latest_data)
    if isinstance(clean_data, dict):
        clean_data["system_config"] = {
            "auto_execution": config.AUTO_EXECUTION,
            "margin_ratio": config.MARGIN_RATIO_PER_TRADE,
            "margin_ratio_pct": int(config.MARGIN_RATIO_PER_TRADE * 100),
            "max_contracts": config.MAX_CONTRACTS_PER_TRADE,
            "leverage": config.LEVERAGE,
            "mode": config.MODE,
            "detected_client_ip": getattr(orch.exchange, "detected_client_ip", "152.59.178.77"),
            "ip_restricted": getattr(orch.exchange, "ip_restricted", False)
        }
    return jsonify(clean_data)

@app.route("/api/set_symbol", methods=["POST"])
def set_symbol():
    """Dynamically switches target coin symbol (e.g. XRP, BTC, ETH, SOL)."""
    global orchestrator, latest_data
    data = request.get_json() or {}
    new_symbol = data.get("symbol", "XRP").upper()
    logger.info(f"Switching target symbol to: {new_symbol}")
    
    config.SYMBOL = new_symbol
    orchestrator = SwarmOrchestrator()
    latest_data = {}
    return jsonify({"success": True, "symbol": new_symbol})

@app.route("/api/trigger_test_scalp", methods=["POST"])
def trigger_test_scalp():
    """Forces an immediate test scalp order so the user can verify position tracking & brackets."""
    global orchestrator, latest_data
    orch = get_orchestrator()
    if not orch.latest_state:
        orch.tick()
        
    state = dict(orch.latest_state.get("state", {}))
    ob = dict(state.get("orderbook", {}))
    mark = state.get("mark_price", 1.3660)
    
    # Ensure test trade has clean test parameters
    ob["spread_pct"] = 0.015
    state["orderbook"] = ob
    
    from bots.base_bot import Signal
    test_sig = Signal(
        bot_name="Manual Test Trigger",
        action="BUY",
        confidence=0.90,
        rationale="User requested immediate test scalp.",
        entry_price=ob.get("best_bid") or mark
    )
    
    risk_res = orch.risk_officer.evaluate_order(test_sig, state)
    if risk_res.get("approved"):
        exec_res = orch.exchange.place_scalp_order(
            side=risk_res["action"],
            contracts=risk_res["contracts"],
            entry_price=risk_res["entry_price"],
            sl_price=risk_res["stop_loss"],
            tp_price=risk_res["take_profit"]
        )
        orch.latest_state["execution_result"] = exec_res
        orch.latest_state["risk_evaluation"] = risk_res
        return jsonify({"success": True, "result": risk_res})
    return jsonify({"success": False, "reason": risk_res.get("reason", "Risk officer vetoed")})

@app.route("/api/close_position", methods=["POST"])
def close_position():
    """Immediately closes any active scalp position at market price."""
    global orchestrator
    orch = get_orchestrator()
    try:
        res = orch.exchange.close_position(reason="MANUAL_CLOSE")
        if res.get("success"):
            orch.latest_state["closed_trade"] = res.get("trade")
            return jsonify(res)
        return jsonify(res), 400
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/toggle_auto_trading", methods=["POST"])
def toggle_auto_trading():
    """Toggles autonomous multi-agent trading loop ON or OFF."""
    config.AUTO_EXECUTION = not config.AUTO_EXECUTION
    status_str = "ENABLED" if config.AUTO_EXECUTION else "PAUSED"
    logger.info(f"Autonomous Trading is now {status_str}")
    return jsonify({"success": True, "auto_execution": config.AUTO_EXECUTION, "status": status_str})

@app.route("/api/set_margin_ratio", methods=["POST"])
def set_margin_ratio():
    """Configures demo fund margin allocation per scalp trade (e.g. 0.25, 0.50, 0.75, 1.0)."""
    data = request.get_json() or {}
    ratio = float(data.get("ratio", 0.25))
    ratio = max(0.05, min(1.0, ratio))
    config.MARGIN_RATIO_PER_TRADE = ratio
    logger.info(f"Updated Margin Ratio Per Trade to: {ratio * 100:.0f}% of available demo fund")
    return jsonify({"success": True, "margin_ratio": ratio, "pct": f"{ratio * 100:.0f}%"})

# Ensure background swarm worker is running even when imported via Gunicorn/WSGI
get_orchestrator()

def main():
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    print("\n" + "="*80)
    print(f"[*] DELTA QUANT WEB DASHBOARD IS RUNNING!")
    print(f"[*] Local Access: http://127.0.0.1:{port}")
    print(f"[*] Network/Cloud Access: http://{host}:{port}")
    print("="*80 + "\n")
    
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
