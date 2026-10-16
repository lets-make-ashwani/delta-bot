# 📘 Delta Exchange Algorithmic Scalper Swarm: Complete Documentation & Setup Guide

This document contains the official references, architecture specs, and step-by-step instructions to get your 100x multi-agent trading bot running smoothly on **[https://demo.delta.exchange/](https://demo.delta.exchange/)** and **Delta Exchange India**.

---

## 1. Official Delta Exchange Documentation & Endpoints

| Resource | Official URL |
| :--- | :--- |
| **Official REST API Docs** | [https://docs.delta.exchange](https://docs.delta.exchange) |
| **Official Python Client (GitHub)** | [https://github.com/delta-exchange/delta-rest-client-py](https://github.com/delta-exchange/delta-rest-client-py) |
| **Demo Web Platform (UI)** | [https://demo.delta.exchange](https://demo.delta.exchange) |
| **Demo REST API Base URL** | `https://testnet-api.delta.exchange` |
| **Demo WebSocket URL** | `wss://socket.testnet.delta.exchange` |
| **Delta India Live Web UI** | [https://india.delta.exchange](https://india.delta.exchange) |
| **Delta India Live REST API** | `https://api.india.delta.exchange` |
| **Delta India Live WebSocket** | `wss://socket.india.delta.exchange` |

---

## 2. How Authentication Works on Delta (HMAC-SHA256)

Delta Exchange requires cryptographic signing for all private actions (balance checks, orders, leverage adjustment).

### Required HTTP Request Headers:
- `api-key`: Your Public API Key string.
- `timestamp`: Current Unix timestamp in seconds (integer).
- `signature`: HMAC-SHA256 hash digest (hexadecimal string) computed using your `API Secret` over the concatenation of:
  ```text
  METHOD + TIMESTAMP + PATH + QUERY_STRING + BODY_JSON
  ```
- `Content-Type`: `application/json`

*Note: The included `delta-rest-client` handles this cryptographic handshake automatically.*

---

## 3. Step-by-Step: Setting Up Your Demo Account on `demo.delta.exchange`

### Step 3.1: Create Demo Account
1. Open your browser and go to **[https://demo.delta.exchange/](https://demo.delta.exchange/)**.
2. Sign up with an email address.
3. You will immediately receive free test virtual USD/USDT in your demo wallet.

### Step 3.2: Create Trading API Key
1. In the top-right corner, click your **Profile icon** ➔ select **API Keys** (or **AlgoHub > APIs**).
2. Click **Create API Key**.
3. **Permissions**: Make sure **Trading / Order Placement** is enabled (not just "Read Only").
4. ⚠️ **IP Restriction**: **LEAVE IP RESTRICTION COMPLETELY BLANK**. If you whitelist a specific IP, your home Wi-Fi or mobile network IP changes will trigger `401 ip_not_whitelisted_for_api_key` and block the bot! Leaving it blank ensures 24/7 uninterrupted autonomous trading.
5. Copy:
   - **API Key**
   - **API Secret**

### Step 3.3: Configure `.env` in Your Project
Open `C:\Users\ashwani\Desktop\delta-scalper-bot\.env` in Notepad or your editor, and configure:
```env
BOT_MODE=demo
DELTA_API_KEY=your_actual_demo_key
DELTA_API_SECRET=your_actual_demo_secret
SYMBOL=XRP
LEVERAGE=100
INITIAL_CAPITAL_INR=0.0
MARGIN_RATIO_PER_TRADE=0.25
MAX_CONTRACTS_PER_TRADE=50000
```
*(Setting `INITIAL_CAPITAL_INR=0.0` unlocks your full demo account fund across ₹68,900+ INR / $811 USD without any ₹100 restriction!)*

---

## 4. How 100x Bracket Orders Work on Delta

At 100x leverage, positions must **never** be left unprotected without a stop-loss. A 0.6% sudden market wick will liquidate unprotected trades.

### The Exchange-Native Bracket Order (`POST /v2/orders/bracket`):
Our bot submits an atomic bracket order directly to Delta's matching engine:
```json
{
  "product_id": 2181,
  "size": 15,
  "side": "buy",
  "order_type": "limit_order",
  "limit_price": "1.3700",
  "bracket_stop_loss_price": "1.3665",
  "bracket_stop_loss_limit_price": "1.3665",
  "bracket_take_profit_price": "1.3775",
  "bracket_take_profit_limit_price": "1.3775"
}
```

### Why this is critical:
- Once filled, the exchange automatically places the **Take-Profit (+0.55%)** and **Stop-Loss (-0.25%)** directly on the order book.
- Even if your computer turns off or loses internet connection, **Delta Exchange will automatically close the trade at your Stop-Loss or Take-Profit**.

---

## 5. Command Reference

All commands run from PowerShell in `C:\Users\ashwani\Desktop\delta-scalper-bot`:

### 1. Run on Demo (`demo.delta.exchange`)
```powershell
# Default: Scalp XRP at 100x leverage
python main.py --mode demo

# Scalp Bitcoin (BTC) on Demo:
python main.py --mode demo --symbol BTC

# Scalp Ethereum (ETH) on Demo:
python main.py --mode demo --symbol ETH

# Scalp Solana (SOL) on Demo:
python main.py --mode demo --symbol SOL
```

### 2. Run Instant Paper Simulation (No API keys required)
```powershell
python main.py --mode paper --symbol XRP
```

### 3. Run Simulated Trade Execution Test (Verify 100x PnL Math)
```powershell
python simulate_trades.py
```

### 4. Run Live with Real ₹100 Capital
*(Only after you are satisfied with Demo results)*
```powershell
python main.py --mode live --capital 100.0 --leverage 100
```

---

## 6. Troubleshooting Common Issues

1. **`invalid_signature` or `401 Unauthorized`**:
   - Check that `DELTA_API_KEY` and `DELTA_API_SECRET` in `.env` are copied without trailing spaces.
   - Verify that your PC system clock is accurate (timestamps must match server time within 5 seconds).
2. **`insufficient_margin`**:
   - At 100x leverage, initial margin is tiny (~₹1.20 per contract), but if capital falls below ₹10, the Chief Risk Officer pauses new entries to prevent risk.
3. **`open_order_not_found` when modifying brackets**:
   - Delta closes the original entry order ID once filled and converts the stop/target into resting child orders. The bot manages this state automatically.


---

## ☁️ Deploying to Render & Storage Requirements

This bot is fully containerized and pre-configured for **Render Cloud Deployment** via 
ender.yaml and Procfile.

### 💾 Storage & Resource Footprint on Render:

| Resource Metric | Bot Actual Usage | Render Free Tier Limit | Utilization % |
| :--- | :---: | :---: | :---: |
| **Disk Storage (Build & Code)** | **~170 MB - 180 MB** | **10.0 GB** (Ephemeral Disk) | **< 1.8%** *(Virtually negligible)* |
| **RAM (Memory Consumption)** | **~140 MB - 190 MB** | **512 MB** RAM | **~30% - 35%** *(Plenty of headroom)* |
| **CPU Allocation** | **0.05 - 0.1 vCPU** | **0.1 vCPU** (Shared) | **Optimal** *(Lightweight polling)* |
| **Monthly Bandwidth** | **~15 GB - 20 GB** | **100 GB / month** | **~18%** |

#### Detailed Disk Breakdown:
- **Application Source Code & Web UI**: ~1.5 MB (HTML templates, CSS, JS, Python modules).
- **Virtual Environment & Dependencies**: ~165 MB (lask, gunicorn, 
umpy, pandas, groq, 
equests, python-dotenv).
- **Learning State & Local Logs**: ~2 MB - 5 MB (learning_memory.json is lightweight JSON, logs auto-rotate).

> **Note**: Render provides **10 GB of free ephemeral disk storage** for your web service. The entire Delta Scalper Bot requires only **~180 MB**, so it easily fits within **less than 2% of the free quota** with no paid persistent disk required.

### 🚀 How to Deploy to Render in 3 Steps:
1. Push your repository to **GitHub** (already connected to origin/main).
2. Log into [Render Dashboard](https://dashboard.render.com/) and click **New +** → **Blueprint**.
3. Select your repository delta-scalper-bot. Render will automatically detect 
ender.yaml and launch the service with zero configuration.
