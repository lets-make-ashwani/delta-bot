# ⚡ Delta Scalper Bot Swarm (100x Multi-Agent Quantitative Desk)

An AI-driven multi-agent algorithmic trading system engineered for **100x scalping** on **[demo.delta.exchange](https://demo.delta.exchange/)** and **Delta Exchange India**.

---

## 🤖 The Swarm Architecture

1. **Market Analyst Bot** ([`bots/market_analyst.py`](file:///C:/Users/ashwani/Desktop/delta-scalper-bot/bots/market_analyst.py)): Ingests real-time candle trends and orderbook bid/ask depth to detect market regimes.
2. **Momentum Scalper Bot** ([`bots/momentum_scalper.py`](file:///C:/Users/ashwani/Desktop/delta-scalper-bot/bots/momentum_scalper.py)): Enters high-probability micro-breakouts during volume expansion.
3. **Mean Reversion Scalper Bot** ([`bots/mean_reversion.py`](file:///C:/Users/ashwani/Desktop/delta-scalper-bot/bots/mean_reversion.py)): Fades overextended Bollinger Band & RSI extremes during range-bound chop.
4. **Strategy Generator Bot** ([`bots/strategy_generator.py`](file:///C:/Users/ashwani/Desktop/delta-scalper-bot/bots/strategy_generator.py)): Dynamically adapts strategy behavior. Tightens stop-losses during volatility spikes.
5. **Chief Risk Officer Bot** ([`bots/risk_guardian.py`](file:///C:/Users/ashwani/Desktop/delta-scalper-bot/bots/risk_guardian.py)): Holds absolute veto power:
   - **Multi-Bullet Sizing**: Divides capital so a single bad trade cannot wipe out the account.
   - **Ultra-Tight Stop-Loss (0.22% - 0.25%)**: Exits losing trades before Delta's 100x liquidation engine triggers.
   - **Take-Profit (0.45% - 0.65%)**: Locks in +45% to +65% ROI on margin at 100x.
   - **Spread Gate**: Blocks trades if the bid-ask spread is wider than 0.06%.

---

## 🚀 How to Trade on https://demo.delta.exchange/

### Step 1: Get Demo API Keys
1. Open your browser and log into **[https://demo.delta.exchange/](https://demo.delta.exchange/)**.
2. Click your **Profile Icon** (top right) -> **API Keys**.
3. Click **Create API Key**.
4. Copy the generated **API Key** and **API Secret**.

### Step 2: Configure Your Bot
In `C:\Users\ashwani\Desktop\delta-scalper-bot`, create or edit a file named `.env`:
```env
BOT_MODE=demo
DELTA_API_KEY=your_demo_key_here
DELTA_API_SECRET=your_demo_secret_here
SYMBOL=XRP
LEVERAGE=100
INITIAL_CAPITAL_INR=0.0
MARGIN_RATIO_PER_TRADE=0.25
MAX_CONTRACTS_PER_TRADE=50000
```
*(Setting `INITIAL_CAPITAL_INR=0.0` automatically connects to your full demo account fund across ₹68,900+ INR / $811 USD without any ₹100 boundary!)*

### Step 3: Run the Bot
Open PowerShell on your Desktop:
```powershell
cd C:\Users\ashwani\Desktop\delta-scalper-bot
python web_server.py
```
*You can open `https://demo.delta.exchange/` in your browser and watch the bot open demo positions and place brackets live on your screen!*

---

## 🖥️ Launching the Interactive Web Dashboard

In addition to the terminal display, we created a full **Visual Web Dashboard** featuring:
- **Jarvis AI ("Jev AI") Brain**: Real-time neural scoring (-100 to +100), market reasoning, and trade verdicts (`STRONG_BUY`, `LEAN_BUY`, `HOLD`, `SELL`).
- **Live Crypto News & Sentiment Feed**: Real-time headlines and sentiment tags (`BULLISH`, `BEARISH`, `NEUTRAL`).
- **Bot Swarm Matrix**: Interactive table showing every bot's vote, confidence score, and rationale.
- **Active 100x Position Card**: Live PnL in ₹, ROI % on margin, Stop-Loss, and Take-Profit brackets.
- **One-Click Coin Switcher**: Switch between `XRP`, `BTC`, `ETH`, and `SOL` with one click!

### How to Launch the Web Dashboard:
```powershell
cd C:\Users\ashwani\Desktop\delta-scalper-bot
python web_server.py
```
Then open your browser at:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🌐 Testing on ANY Market

You can run the bot on any coin simply by adding the `--symbol` flag:

```powershell
# Trade XRP on Demo:
python main.py --mode demo --symbol XRP

# Trade Bitcoin on Demo:
python main.py --mode demo --symbol BTC

# Trade Ethereum on Demo:
python main.py --mode demo --symbol ETH

# Trade Solana on Demo:
python main.py --mode demo --symbol SOL
```

---

## 🧪 Testing in Zero-Risk Paper Mode (No API Keys Needed)
Want to test immediately without logging into anything?
```powershell
python main.py --mode paper --symbol XRP
```
Runs against live market feeds with a simulated ₹100 INR account.
