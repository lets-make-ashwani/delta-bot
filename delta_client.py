"""
Unified Delta Exchange Client.
Provides a unified interface for:
1. DEMO MODE: Connects to https://demo.delta.exchange (via https://testnet-api.delta.exchange) using demo API keys.
2. PAPER MODE: Real-time simulation on live market price/spread feeds with virtual ₹100 INR.
3. LIVE MODE: Connects to Delta Exchange India live account with real funds.
"""

import time
import logging
from typing import Dict, Any, Optional, List
import requests
from delta_rest_client import DeltaRestClient, OrderType
from config import config

logger = logging.getLogger("DeltaClient")

class PaperTradingEngine:
    """Simulates 100x leverage margin trading using live order book and tick data."""
    def __init__(self, initial_capital_inr: float = 100.0, leverage: int = 100, usd_inr_rate: float = 86.5):
        self.initial_capital_inr = initial_capital_inr
        self.balance_inr = initial_capital_inr
        self.leverage = leverage
        self.usd_inr_rate = usd_inr_rate
        self.position: Optional[Dict[str, Any]] = None
        self.trades = []
        self.liquidations = 0

    def get_balance(self) -> Dict[str, float]:
        unrealized_pnl = 0.0
        if self.position:
            unrealized_pnl = self.position.get("unrealized_pnl_inr", 0.0)
        return {
            "balance_inr": round(self.balance_inr, 2),
            "equity_inr": round(self.balance_inr + unrealized_pnl, 2),
            "unrealized_pnl_inr": round(unrealized_pnl, 2),
            "available_margin_inr": round(self.balance_inr - (self.position.get("margin_inr", 0.0) if self.position else 0.0), 2)
        }

    def open_position(self, symbol: str, side: str, contracts: int, entry_price: float, sl_price: float, tp_price: float) -> Dict[str, Any]:
        if self.position is not None:
            return {"success": False, "error": "Position already open"}
        
        notional_usd = contracts * entry_price
        notional_inr = notional_usd * self.usd_inr_rate
        margin_inr = notional_inr / self.leverage
        
        fee_inr = notional_inr * 0.0002  # 0.02% maker fee
        if margin_inr + fee_inr > self.balance_inr:
            return {"success": False, "error": f"Insufficient margin. Required: INR {margin_inr + fee_inr:.2f}, Balance: INR {self.balance_inr:.2f}"}

        self.balance_inr -= fee_inr
        
        # At 100x, liquidation distance is ~0.65%
        liq_distance_pct = 0.0065
        if side.upper() == "BUY":
            liq_price = entry_price * (1 - liq_distance_pct)
        else:
            liq_price = entry_price * (1 + liq_distance_pct)

        self.position = {
            "symbol": symbol,
            "side": side.upper(),
            "contracts": contracts,
            "entry_price": entry_price,
            "stop_loss": sl_price,
            "take_profit": tp_price,
            "liquidation_price": round(liq_price, 4),
            "margin_inr": margin_inr,
            "notional_inr": notional_inr,
            "open_time": time.time(),
            "entry_fee_inr": fee_inr,
            "unrealized_pnl_inr": 0.0
        }
        logger.info(f"🟢 [PAPER EXECUTION] {side} {contracts} contracts @ ${entry_price:.4f} | Margin: INR {margin_inr:.2f} | SL: ${sl_price:.4f} | TP: ${tp_price:.4f}")
        return {"success": True, "position": self.position}

    def update_price(self, current_price: float) -> Optional[Dict[str, Any]]:
        """Checks if current price triggers Take Profit, Stop Loss, or Liquidation."""
        if not self.position:
            return None

        side = self.position["side"]
        entry = self.position["entry_price"]
        sl = self.position["stop_loss"]
        tp = self.position["take_profit"]
        liq = self.position["liquidation_price"]
        notional_inr = self.position["notional_inr"]

        if side == "BUY":
            price_change_pct = (current_price - entry) / entry
        else:
            price_change_pct = (entry - current_price) / entry

        pnl_inr = notional_inr * price_change_pct
        self.position["unrealized_pnl_inr"] = pnl_inr

        # 1. Check Liquidation
        if (side == "BUY" and current_price <= liq) or (side == "SELL" and current_price >= liq):
            return self._close_position(current_price, reason="LIQUIDATION", exit_fee_ratio=0.001)

        # 2. Check Stop Loss
        if (side == "BUY" and current_price <= sl) or (side == "SELL" and current_price >= sl):
            return self._close_position(current_price, reason="STOP_LOSS", exit_fee_ratio=0.0002)

        # 3. Check Take Profit
        if (side == "BUY" and current_price >= tp) or (side == "SELL" and current_price <= tp):
            return self._close_position(current_price, reason="TAKE_PROFIT", exit_fee_ratio=0.0002)

        return None

    def _close_position(self, exit_price: float, reason: str, exit_fee_ratio: float = 0.0002) -> Dict[str, Any]:
        pos = self.position
        side = pos["side"]
        entry = pos["entry_price"]
        notional_inr = pos["notional_inr"]

        if side == "BUY":
            pnl_pct = (exit_price - entry) / entry
        else:
            pnl_pct = (entry - exit_price) / entry

        exit_fee_inr = notional_inr * exit_fee_ratio
        raw_pnl_inr = notional_inr * pnl_pct
        
        if reason == "LIQUIDATION":
            net_pnl_inr = -pos["margin_inr"]
            self.liquidations += 1
        else:
            net_pnl_inr = raw_pnl_inr - exit_fee_inr

        self.balance_inr = max(0.0, self.balance_inr + net_pnl_inr)

        trade_result = {
            "symbol": pos["symbol"],
            "side": side,
            "contracts": pos["contracts"],
            "entry_price": entry,
            "exit_price": exit_price,
            "reason": reason,
            "pnl_inr": round(net_pnl_inr, 2),
            "pnl_pct_on_margin": round((net_pnl_inr / pos["margin_inr"]) * 100, 2),
            "new_balance_inr": round(self.balance_inr, 2),
            "duration_sec": round(time.time() - pos["open_time"], 1)
        }
        self.trades.append(trade_result)
        self.position = None
        return trade_result


class DeltaExchangeManager:
    """Manages Delta REST client interactions and wraps Demo and Paper trading seamlessly."""
    def __init__(self, target_symbol: Optional[str] = None):
        self.mode = config.MODE
        raw_symbol = (target_symbol or config.SYMBOL).upper()
        
        # 1. Dynamically resolve product details on target exchange
        self.target_url = config.INDIA_LIVE_URL if self.mode == "live" else config.DEMO_API_URL
        self.product = self._resolve_product(raw_symbol, self.target_url)
        self.symbol = self.product["symbol"]
        self.product_id = self.product["id"]
        self.tick_size = float(self.product.get("tick_size", "0.0001"))
        
        # Real live intelligence client (fetches live market candles & quotes)
        self.live_intel_client = DeltaRestClient(base_url=config.INDIA_LIVE_URL)
        
        # Authenticated execution client (for demo or live)
        self.auth_client = None
        if self.mode in ["demo", "testnet", "live"] and config.API_KEY and config.API_SECRET:
            self.auth_client = DeltaRestClient(
                base_url=self.target_url,
                api_key=config.API_KEY,
                api_secret=config.API_SECRET
            )
            logger.info(f"Connected to Delta in {self.mode.upper()} mode at {self.target_url}")
            try:
                self.auth_client.set_leverage(self.product_id, config.LEVERAGE)
                logger.info(f"Set {config.LEVERAGE}x leverage for {self.symbol} (ID: {self.product_id})")
            except Exception as e:
                logger.warning(f"Could not automatically set leverage: {e}")
        else:
            if self.mode in ["demo", "testnet"] and (not config.API_KEY or not config.API_SECRET):
                logger.warning(f"No API key provided for DEMO mode. Falling back to PAPER trading mode.")
                self.mode = "paper"

        # Local Paper Engine
        self.paper = PaperTradingEngine(
            initial_capital_inr=config.INITIAL_CAPITAL_INR,
            leverage=config.LEVERAGE,
            usd_inr_rate=config.USD_INR_RATE
        )
        
        # Real-Time Trade & Profit/Loss Ledger
        self.trade_history: List[Dict[str, Any]] = []
        self.last_active_pos: Optional[Dict[str, Any]] = None
        
        # Auto-sync past realized trades on startup
        if self.auth_client:
            self.sync_demo_trade_history()

    def _resolve_product(self, raw_symbol: str, base_url: str) -> Dict[str, Any]:
        """Auto-discovers product specifications from Delta API based on user input (e.g. XRP, BTC, ETH)."""
        clean_name = raw_symbol.replace("USD", "").replace("USDT", "").replace("_INR", "")
        try:
            r = requests.get(f"{base_url}/v2/products", timeout=5)
            if r.status_code == 200:
                products = r.json().get("result", [])
                # Look for perpetual futures matching the clean coin name
                for p in products:
                    sym = p.get("symbol", "")
                    if clean_name in sym and p.get("contract_type") == "perpetual_futures":
                        return p
                # Fallback to any product with symbol
                for p in products:
                    if clean_name in p.get("symbol", ""):
                        return p
        except Exception as e:
            logger.error(f"Error resolving product on {base_url}: {e}")

        # Default fallback
        if "deltaex.org" in base_url or "cdn-ind" in base_url:
            return {"id": 93723, "symbol": "XRPUSD", "tick_size": "0.0001"}
        if "testnet" in base_url or "demo" in base_url:
            return {"id": 2181, "symbol": "XRPUSDT", "tick_size": "0.0001"}
        return {"id": 14969, "symbol": "XRPUSD", "tick_size": "0.0001"}

    def fetch_live_ticker(self) -> Dict[str, Any]:
        """Fetches live ticker and best bid/ask quotes."""
        try:
            # Query the target exchange first
            r = requests.get(f"{self.target_url}/v2/tickers/{self.symbol}", timeout=4)
            if r.status_code == 200:
                res = r.json().get("result", {})
                if res and res.get("quotes"):
                    return res
        except Exception:
            pass

        # Fallback to live India ticker
        live_sym = "XRPUSD" if "XRP" in self.symbol else self.symbol
        try:
            return self.live_intel_client.get_ticker(live_sym)
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            return {}

    def fetch_candles(self, count: int = 60, resolution: str = "1m") -> list:
        """Fetches 1-minute historical candles from high-volume live feed."""
        now = int(time.time())
        start = now - (count * 60)
        # Use live India feed for rich candle history
        live_sym = "XRPUSD" if "XRP" in self.symbol else ("BTCUSD" if "BTC" in self.symbol else "ETHUSD")
        try:
            candles = self.live_intel_client.get_candles(live_sym, resolution=resolution, start=start, end=now)
            if isinstance(candles, list):
                return candles
            elif isinstance(candles, dict):
                return candles.get("result", [])
        except Exception as e:
            logger.error(f"Error fetching live candles: {e}")
        return []

    def get_balance(self) -> Dict[str, float]:
        if self.mode == "paper":
            return self.paper.get_balance()
        elif self.auth_client:
            try:
                bal = self.auth_client.get_all_wallet_balances()
                if isinstance(bal, list):
                    usd_item = next((item for item in bal if item.get("asset_symbol") == "USD"), None)
                    if usd_item:
                        balance_inr = float(usd_item.get("balance_inr") or 0.0)
                        avail_inr = float(usd_item.get("available_balance_inr") or 0.0)
                        return {
                            "balance_inr": round(balance_inr, 2),
                            "available_margin_inr": round(avail_inr, 2),
                            "equity_inr": round(balance_inr, 2),
                            "unrealized_pnl_inr": 0.0,
                            "raw_balance": bal
                        }
                elif isinstance(bal, dict):
                    meta = bal.get("meta", {})
                    net_equity = float(meta.get("net_equity") or 0.0)
                    if net_equity > 0:
                        return {
                            "balance_inr": round(net_equity, 2),
                            "equity_inr": round(net_equity, 2),
                            "unrealized_pnl_inr": 0.0,
                            "raw_balance": bal
                        }
            except Exception as e:
                logger.debug(f"Could not refresh live wallet balance: {e}")
        return {"balance_inr": config.INITIAL_CAPITAL_INR or 50000.0, "equity_inr": config.INITIAL_CAPITAL_INR or 50000.0}

    def sync_demo_trade_history(self):
        """Fetches fills from Delta API and extracts realized trades and profits/losses."""
        if not self.auth_client:
            return
        try:
            fills_res = self.auth_client.fills()
            fills_list = fills_res.get("result", []) if isinstance(fills_res, dict) else (fills_res if isinstance(fills_res, list) else [])
            
            parsed_trades = []
            seen_ids = set()
            for f in fills_list:
                meta = f.get("meta_data", {})
                new_pos = meta.get("new_position", {})
                realized_pnl_str = new_pos.get("realized_pnl")
                fill_id = f.get("id") or f.get("order_id")
                
                # Check if this fill closed a position with realized PnL
                if realized_pnl_str and str(realized_pnl_str) != "0" and fill_id not in seen_ids:
                    seen_ids.add(fill_id)
                    pnl_usd = float(realized_pnl_str)
                    pnl_inr = round(pnl_usd * config.USD_INR_RATE, 2)
                    contracts = int(float(f.get("size", 0)))
                    price = float(f.get("price", 0.0))
                    side = f.get("side", "").upper()
                    
                    parsed_trades.append({
                        "id": fill_id,
                        "symbol": f.get("product_symbol", self.symbol),
                        "side": side,
                        "contracts": contracts,
                        "exit_price": price,
                        "pnl_usd": round(pnl_usd, 2),
                        "pnl_inr": pnl_inr,
                        "pnl_pct_on_margin": round((pnl_usd / max(1.0, (contracts * price / config.LEVERAGE))) * 100, 2),
                        "reason": "TAKE_PROFIT" if pnl_usd > 0 else "STOP_LOSS",
                        "timestamp": f.get("created_at", "")
                    })
            if parsed_trades:
                self.trade_history = parsed_trades
                logger.info(f"Synchronized {len(self.trade_history)} realized demo trades from Delta.")
        except Exception as e:
            logger.debug(f"Could not sync fills trade history: {e}")

    def get_active_position(self) -> Optional[Dict[str, Any]]:
        """Returns the active position directly from Delta Demo servers or Paper engine with live mark-to-market PnL."""
        if self.mode in ["demo", "live"] and self.auth_client:
            try:
                m_pos = self.auth_client.get_margined_position(self.product_id)
                if isinstance(m_pos, dict) and m_pos.get("size"):
                    raw_size = int(m_pos["size"])
                    if raw_size != 0:
                        side = "BUY" if raw_size > 0 else "SELL"
                        entry = float(m_pos.get("entry_price") or 0.0)
                        liq = float(m_pos.get("liquidation_price") or 0.0)
                        margin_usd = float(m_pos.get("margin") or 0.0)
                        
                        # Live mark-to-market PnL
                        ticker = self.fetch_live_ticker()
                        mark = float(ticker.get("mark_price") or entry)
                        
                        if side == "BUY":
                            live_pnl_usd = (mark - entry) * abs(raw_size)
                        else:
                            live_pnl_usd = (entry - mark) * abs(raw_size)
                        live_pnl_inr = round(live_pnl_usd * config.USD_INR_RATE, 2)
                        
                        # Preserve dynamic adjusted SL and TP targets if already tuned by Strategy Generator
                        if self.last_active_pos and self.last_active_pos.get("stop_loss"):
                            sl_price = self.last_active_pos["stop_loss"]
                        else:
                            sl_price = round(entry * (0.9975 if side == "BUY" else 1.0025), 4)

                        if self.last_active_pos and self.last_active_pos.get("take_profit"):
                            tp_price = self.last_active_pos["take_profit"]
                        else:
                            tp_price = round(entry * (1.0055 if side == "BUY" else 0.9945), 4)
                        
                        pos_dict = {
                            "symbol": self.symbol,
                            "side": side,
                            "contracts": abs(raw_size),
                            "entry_price": round(entry, 4),
                            "mark_price": round(mark, 4),
                            "stop_loss": sl_price,
                            "take_profit": tp_price,
                            "liquidation_price": round(liq, 4),
                            "margin_inr": round(margin_usd * config.USD_INR_RATE, 2),
                            "unrealized_pnl_inr": live_pnl_inr,
                            "unrealized_pnl_usd": round(live_pnl_usd, 2),
                            "highest_price": self.last_active_pos.get("highest_price", mark) if self.last_active_pos else mark,
                            "lowest_price": self.last_active_pos.get("lowest_price", mark) if self.last_active_pos else mark,
                            "open_time": self.last_active_pos.get("open_time", time.time()) if self.last_active_pos else time.time()
                        }
                        self.last_active_pos = pos_dict
                        return pos_dict
                
                # If size == 0 or position is closed:
                if self.last_active_pos is not None:
                    logger.info("🟢 Active position closed on Delta Exchange. Refreshing trade history...")
                    self.sync_demo_trade_history()
                    self.last_active_pos = None

            except Exception as e:
                logger.debug(f"Could not refresh live position: {e}")

        if self.mode == "paper":
            return self.paper.position
        return None

    def close_position(self, reason: str = "MANUAL_CLOSE") -> Dict[str, Any]:
        """Closes any active position at market price across Demo, Live, or Paper mode."""
        if self.mode == "paper" and self.paper.position:
            mark = float(self.fetch_live_ticker().get("mark_price", 1.3680))
            res = self.paper._close_position(mark, reason=reason)
            return {"success": True, "trade": res}

        elif self.mode in ["demo", "live"] and self.auth_client:
            pos = self.last_active_pos or self.get_active_position()
            if not pos:
                return {"success": False, "reason": "No active position on Delta to close."}

            contracts = pos["contracts"]
            side = pos["side"]
            exit_side = "sell" if side == "BUY" else "buy"

            # 1. Cancel pending stop/take profit orders to prevent orphan execution
            try:
                self.auth_client.cancel_all_orders({'product_id': self.product_id})
                logger.info(f"Cancelled all pending orders for product {self.product_id}")
            except Exception as e:
                logger.warning(f"Error cancelling pending orders: {e}")

            # 2. Place market close order
            try:
                close_res = self.auth_client.place_order(
                    product_id=self.product_id,
                    size=int(contracts),
                    side=exit_side,
                    order_type=OrderType.MARKET,
                    reduce_only='true'
                )
                logger.info(f"Market close executed for {contracts} contracts: {close_res}")
                time.sleep(0.5)
                self.sync_demo_trade_history()
                self.last_active_pos = None
                return {"success": True, "result": close_res, "reason": reason}
            except Exception as e:
                logger.error(f"Error executing market close: {e}")
                # Fallback to Delta position close API
                try:
                    close_all_res = self.auth_client.close_all_positions(close_all_isolated=True, product_ids=[self.product_id])
                    time.sleep(0.5)
                    self.sync_demo_trade_history()
                    self.last_active_pos = None
                    return {"success": True, "result": close_all_res, "reason": reason}
                except Exception as e2:
                    return {"success": False, "error": f"{e} | Fallback failed: {e2}"}

        return {"success": False, "reason": "No active trading engine"}

    def update_stop_loss_order(self, new_sl_price: float, side: str, contracts: int) -> Dict[str, Any]:
        """Updates or cancels/replaces the server-side stop-loss order on Delta to track the dynamic trailing stop."""
        if not self.auth_client:
            return {"success": False, "reason": "No auth client"}
        try:
            # 1. Cancel existing stop orders for this product
            self.auth_client.cancel_all_orders({'product_id': self.product_id})
            
            # 2. Place updated stop-loss order
            stop_side = "sell" if side.upper() == "BUY" else "buy"
            res = self.auth_client.place_stop_order(
                product_id=self.product_id,
                size=int(contracts),
                side=stop_side,
                stop_price=str(new_sl_price),
                limit_price=str(new_sl_price),
                order_type=OrderType.LIMIT
            )
            logger.info(f"🔄 [ADAPTIVE STOP UPDATED] Server Stop-Loss moved to ${new_sl_price} on Delta")
            return {"success": True, "result": res}
        except Exception as e:
            logger.debug(f"Adaptive stop-loss update note: {e}")
            return {"success": False, "error": str(e)}

    def get_trade_metrics(self) -> Dict[str, Any]:
        """Calculates cumulative PnL, win rate, and total closed trade performance."""
        trades = self.paper.trades if self.mode == "paper" else self.trade_history
        total_pnl_inr = sum(t.get("pnl_inr", 0.0) for t in trades)
        wins = [t for t in trades if t.get("pnl_inr", 0.0) > 0]
        losses = [t for t in trades if t.get("pnl_inr", 0.0) < 0]
        total_count = len(trades)
        win_rate = round((len(wins) / total_count * 100), 1) if total_count > 0 else 0.0

        return {
            "trades": trades,
            "total_trades": total_count,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": win_rate,
            "total_pnl_inr": round(total_pnl_inr, 2)
        }

    def place_scalp_order(self, side: str, contracts: int, entry_price: float, sl_price: float, tp_price: float) -> Dict[str, Any]:
        """Places a scalp order with Stop-Loss protection on Demo exchange or executes on Paper engine."""
        if self.mode == "paper":
            return self.paper.open_position(self.symbol, side, contracts, entry_price, sl_price, tp_price)
        
        elif self.auth_client:
            try:
                # 1. Place Primary Entry Order on Delta
                entry_res = self.auth_client.place_order(
                    product_id=self.product_id,
                    size=int(contracts),
                    side=side.lower(),
                    limit_price=str(entry_price),
                    order_type=OrderType.LIMIT
                )
                logger.info(f"Entry order placed on {self.mode.upper()}: {entry_res}")

                # 2. Place Attached Stop Loss Protection
                stop_side = "sell" if side.lower() == "buy" else "buy"
                try:
                    stop_res = self.auth_client.place_stop_order(
                        product_id=self.product_id,
                        size=int(contracts),
                        side=stop_side,
                        stop_price=str(sl_price),
                        limit_price=str(sl_price),
                        order_type=OrderType.LIMIT
                    )
                    logger.info(f"Stop-Loss order placed on {self.mode.upper()}: {stop_res}")
                except Exception as e_sl:
                    logger.warning(f"Stop-loss attachment note: {e_sl}")

                # Update memory tracking
                self.last_active_pos = {
                    "symbol": self.symbol,
                    "side": side.upper(),
                    "contracts": int(contracts),
                    "entry_price": float(entry_price),
                    "stop_loss": float(sl_price),
                    "take_profit": float(tp_price),
                    "margin_inr": round((int(contracts) * float(entry_price) * config.USD_INR_RATE) / config.LEVERAGE, 2),
                    "open_time": time.time()
                }

                return {"success": True, "result": entry_res}
            except Exception as e:
                logger.error(f"Error placing scalp order: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "No trading engine available"}
