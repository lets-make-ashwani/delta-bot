"""
Test simulation runner:
Feeds a simulated price fluctuation to the Paper Trading Engine to demonstrate
how 100x leverage Stop-Loss, Take-Profit, and PnL mechanics execute in real-time.
"""

from delta_client import PaperTradingEngine

def run_simulation():
    print("=" * 70)
    print("SIMULATING 100x LEVERAGE TRADES (Starting Balance: INR 100.00)")
    print("=" * 70)

    engine = PaperTradingEngine(initial_capital_inr=100.0, leverage=100)

    # 1. Simulate a Winning Long Trade (+0.50% price move)
    print("\n[SCENARIO 1: LONG TRADE - TAKE PROFIT TRIGGERED]")
    entry = 1.3600
    tp = 1.3668  # +0.50% move
    sl = 1.3566  # -0.25% stop
    contracts = 15 # 15 XRP (~INR 17.5 margin)

    engine.open_position("XRPUSD", "BUY", contracts, entry, sl, tp)
    print(f"Opened BUY 15 XRP @ ${entry} | Margin: INR {engine.position['margin_inr']:.2f}")

    # Price steps up
    for step_price in [1.3620, 1.3645, 1.3670]:
        print(f"Price tick: ${step_price:.4f}...")
        res = engine.update_price(step_price)
        if res:
            print(f"--> EXIT TRIGGERED: {res['reason']}! Profit: +INR {res['pnl_inr']:.2f} ({res['pnl_pct_on_margin']:+.1f}% on margin)")
            break

    bal = engine.get_balance()
    print(f"Account Balance after Trade 1: INR {bal['balance_inr']:.2f}")

    # 2. Simulate a Stopped-Out Short Trade (-0.25% stop loss hit)
    print("\n[SCENARIO 2: SHORT TRADE - STOP LOSS TRIGGERED]")
    entry = 1.3700
    tp = 1.3625  # -0.55%
    sl = 1.3734  # +0.25% stop
    contracts = 15

    engine.open_position("XRPUSD", "SELL", contracts, entry, sl, tp)
    print(f"Opened SELL 15 XRP @ ${entry} | Margin: INR {engine.position['margin_inr']:.2f}")

    for step_price in [1.3715, 1.3735]:
        print(f"Price tick: ${step_price:.4f}...")
        res = engine.update_price(step_price)
        if res:
            print(f"--> EXIT TRIGGERED: {res['reason']}! Loss: INR {res['pnl_inr']:.2f} ({res['pnl_pct_on_margin']:+.1f}% on margin)")
            break

    bal = engine.get_balance()
    print(f"Account Balance after Trade 2: INR {bal['balance_inr']:.2f}")
    print("\n" + "=" * 70)
    print("CONCLUSION: Notice how the Stop-Loss cut the loss to only ~INR 4.50,")
    print("protecting the account from being wiped out at 100x leverage!")
    print("=" * 70)

if __name__ == "__main__":
    run_simulation()
