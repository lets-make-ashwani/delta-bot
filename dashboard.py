"""
Visual Terminal Dashboard for Delta Scalper Swarm.
Displays real-time bot communication, 100x position tracking, and performance.
Cross-platform and Windows-terminal safe.
"""

import sys
from typing import Dict, Any

# Ensure standard output supports UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"

def render_dashboard(tick_data: Dict[str, Any]):
    state = tick_data["state"]
    mark_price = state.get("mark_price", 0.0)
    ob = state.get("orderbook", {})
    balance_info = state.get("balance_info", {})
    regime = state.get("regime", "UNKNOWN")
    profile = tick_data.get("strategy_profile", {})
    
    mom_sig = tick_data.get("mom_signal")
    mr_sig = tick_data.get("mr_signal")
    risk_eval = tick_data.get("risk_evaluation")
    closed = tick_data.get("closed_trade")
    
    active_pos = state.get("active_position")

    print("\n" + "="*80)
    print(f"{Colors.BOLD}{Colors.CYAN}>> DELTA EXCHANGE INDIA - 100x SCALPER BOT SWARM <<{Colors.RESET}")
    print("="*80)

    # 1. Account & Market Summary
    bal = balance_info.get("balance_inr", 100.0)
    eq = balance_info.get("equity_inr", 100.0)
    pnl_unrealized = balance_info.get("unrealized_pnl_inr", 0.0)
    pnl_color = Colors.GREEN if pnl_unrealized >= 0 else Colors.RED

    print(f"[*] Balance: {Colors.BOLD}INR {bal:.2f}{Colors.RESET} | Equity: {pnl_color}INR {eq:.2f}{Colors.RESET} | Symbol: {Colors.BOLD}{state['symbol']}{Colors.RESET} (100x Leverage)")
    print(f"[*] Mark: ${mark_price:.4f} | Bid: ${ob.get('best_bid', 0):.4f} | Ask: ${ob.get('best_ask', 0):.4f} | Spread: {ob.get('spread_pct', 0):.3f}% | Book Imbalance: {ob.get('imbalance', 0):+.2f}")
    print(f"[*] Market Regime: {Colors.MAGENTA}{Colors.BOLD}{regime}{Colors.RESET} | Strategy Mode: {Colors.YELLOW}{profile.get('mode', 'BALANCED')}{Colors.RESET} (SL: {profile.get('dynamic_sl_pct', 0.25):.2f}%, TP: {profile.get('dynamic_tp_pct', 0.55):.2f}%)")
    print("-" * 80)

    # 2. Swarm Deliberation
    print(f"{Colors.BOLD}[BOT SWARM DELIBERATION]:{Colors.RESET}")
    def print_sig(name, sig):
        if not sig: return
        act_col = Colors.GREEN if sig.action == "BUY" else (Colors.RED if sig.action == "SELL" else Colors.GRAY)
        print(f"  > {name:<22}: {act_col}[{sig.action}]{Colors.RESET} (Conf: {sig.confidence:.2f}) -> {sig.rationale}")

    print_sig("Liquidity Wick Sweep", tick_data.get("wick_signal"))
    print_sig("VWAP Sniper", tick_data.get("vwap_signal"))
    print_sig("Order Book Wall Scalper", tick_data.get("wall_signal"))
    print_sig("RSI Divergence", tick_data.get("div_signal"))
    print_sig("Momentum Scalper", tick_data.get("mom_signal"))
    print_sig("Mean Reversion", tick_data.get("mr_signal"))
    print_sig("News & Sentiment", tick_data.get("news_signal"))
    print_sig("Jarvis AI Brain", tick_data.get("jarvis_signal"))

    # 3. Chief Risk Officer & Execution Status
    if risk_eval:
        if risk_eval.get("approved"):
            print(f"  > {Colors.GREEN}Chief Risk Officer: [APPROVED]{Colors.RESET} {risk_eval['rationale']}")
        else:
            print(f"  > {Colors.YELLOW}Chief Risk Officer: [VETOED]{Colors.RESET} {risk_eval.get('reason')}")

    # 4. Active Position Monitor
    print("-" * 80)
    if active_pos:
        side = active_pos["side"]
        side_col = Colors.GREEN if side == "BUY" else Colors.RED
        pnl = active_pos.get("unrealized_pnl_inr", 0.0)
        pnl_c = Colors.GREEN if pnl >= 0 else Colors.RED
        roi_on_margin = (pnl / active_pos["margin_inr"]) * 100 if active_pos["margin_inr"] > 0 else 0
        
        print(f"{Colors.BOLD}[ACTIVE POSITION]:{Colors.RESET} {side_col}{side} {active_pos['contracts']} XRP{Colors.RESET} @ ${active_pos['entry_price']:.4f}")
        print(f"   Margin: INR {active_pos['margin_inr']:.2f} | Stop-Loss: ${active_pos['stop_loss']:.4f} | Take-Profit: ${active_pos['take_profit']:.4f} | Liq: ${active_pos['liquidation_price']:.4f}")
        print(f"   Unrealized PnL: {pnl_c}{Colors.BOLD}INR {pnl:+.2f} ({roi_on_margin:+.1f}% ROI on margin){Colors.RESET}")
    else:
        print(f"{Colors.GRAY}[Active Position]: No active trade. Bots scanning market for sniper entry...{Colors.RESET}")

    # 5. Closed Trade Alert
    if closed:
        icon = "[+]" if closed["pnl_inr"] > 0 else "[-]"
        col = Colors.GREEN if closed["pnl_inr"] > 0 else Colors.RED
        print("=" * 80)
        print(f"{icon} {Colors.BOLD}TRADE RESULT [{closed['reason']}]:{Colors.RESET} PnL: {col}INR {closed['pnl_inr']:+.2f} ({closed['pnl_pct_on_margin']:+.1f}% on margin){Colors.RESET} | New Balance: INR {closed['new_balance_inr']:.2f}")

    print("=" * 80)
