/**
 * Delta Quant Swarm - Frontend Controller
 * Fully Autonomous Multi-Agent Trading Desk & Live Synchronizer
 */

let activeSymbol = "XRP";
let lastLogText = "";
let isAutoPilot = true;

document.addEventListener("DOMContentLoaded", () => {
  initSymbolButtons();
  initActionButtons();
  initFundRatioButtons();
  initMobileNavigation();
  startClock();
  startPolling();
});

function initMobileNavigation() {
  const pills = document.querySelectorAll(".mobile-pill");
  pills.forEach(pill => {
    pill.addEventListener("click", (e) => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
    });
  });

  // Track scroll position to update active pill
  window.addEventListener("scroll", () => {
    const sections = ["sec-radar", "sec-ai", "sec-position", "sec-swarm", "sec-learning", "sec-trades", "sec-news", "sec-terminal"];
    const scrollPos = window.scrollY + 140;

    for (let i = sections.length - 1; i >= 0; i--) {
      const el = document.getElementById(sections[i]);
      if (el && el.offsetTop <= scrollPos) {
        pills.forEach(p => {
          if (p.getAttribute("href") === `#${sections[i]}`) {
            p.classList.add("active");
          } else {
            p.classList.remove("active");
          }
        });
        break;
      }
    }
  }, { passive: true });
}

function initActionButtons() {
  // 1. Force Test Scalp
  const btnTest = document.getElementById("btn-test-scalp");
  if (btnTest) {
    btnTest.addEventListener("click", async () => {
      btnTest.innerText = "⏳ Placing Order...";
      try {
        const res = await fetch("/api/trigger_test_scalp", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          addLog("⚡ [MANUAL TRIGGER] 100x Scalp order placed successfully with bracket SL/TP!", "trade");
        } else {
          addLog(`⚠️ [ORDER BLOCKED]: ${data.reason}`, "warn");
        }
      } catch (err) {
        addLog(`❌ Error triggering scalp: ${err}`, "warn");
      } finally {
        btnTest.innerText = "⚡ Force Test Scalp";
        pollStatus();
      }
    });
  }

  // 2. Manual Close Position
  const btnClose = document.getElementById("btn-close-pos");
  if (btnClose) {
    btnClose.addEventListener("click", async () => {
      btnClose.innerText = "⏳ Closing...";
      try {
        const res = await fetch("/api/close_position", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          addLog("🛑 Position manually closed at market price.", "warn");
        } else {
          addLog(`⚠️ Close notice: ${data.reason || data.error}`, "warn");
        }
      } catch (err) {
        console.error(err);
      } finally {
        btnClose.innerText = "🛑 Close Position";
        pollStatus();
      }
    });
  }

  // 3. Auto-Pilot Toggle
  const btnAuto = document.getElementById("btn-toggle-auto");
  if (btnAuto) {
    btnAuto.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/toggle_auto_trading", { method: "POST" });
        const data = await res.json();
        isAutoPilot = data.auto_execution;
        updateAutoButtonUI(isAutoPilot);
        addLog(`🤖 Autonomous execution ${data.status}`, isAutoPilot ? "trade" : "warn");
      } catch (err) {
        console.error("Error toggling auto-trading:", err);
      }
    });
  }
}

function updateAutoButtonUI(active) {
  const btnAuto = document.getElementById("btn-toggle-auto");
  if (!btnAuto) return;
  if (active) {
    btnAuto.innerText = "🤖 AUTO-PILOT: ACTIVE";
    btnAuto.style.background = "rgba(34, 197, 94, 0.18)";
    btnAuto.style.color = "var(--green)";
    btnAuto.style.borderColor = "var(--green)";
  } else {
    btnAuto.innerText = "⏸️ AUTO-PILOT: PAUSED";
    btnAuto.style.background = "rgba(245, 158, 11, 0.18)";
    btnAuto.style.color = "var(--gold)";
    btnAuto.style.borderColor = "var(--gold)";
  }
}

function initFundRatioButtons() {
  document.querySelectorAll(".ratio-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".ratio-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const ratio = parseFloat(btn.dataset.ratio);
      try {
        const res = await fetch("/api/set_margin_ratio", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ratio })
        });
        const data = await res.json();
        addLog(`Fund Allocation set to ${data.pct} of available demo balance per trade`, "info");
      } catch (err) {
        console.error("Error setting fund ratio:", err);
      }
    });
  });
}

function initSymbolButtons() {
  document.querySelectorAll(".sym-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".sym-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeSymbol = btn.dataset.symbol;
      
      try {
        await fetch("/api/set_symbol", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol: activeSymbol })
        });
        addLog(`Switched target symbol to [${activeSymbol}]`, "info");
      } catch (err) {
        console.error("Error setting symbol:", err);
      }
    });
  });
}

function startClock() {
  setInterval(() => {
    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0];
    const el = document.getElementById("clock-display");
    if (el) el.innerText = timeStr;
  }, 1000);
}

function startPolling() {
  pollStatus();
  setInterval(pollStatus, 1500);
}

async function pollStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();
    renderDashboard(data);
  } catch (err) {
    // Polling error silently caught
  }
}

function renderDashboard(data) {
  if (!data || !data.state) return;

  const state = data.state;
  const ob = state.orderbook || {};
  const bal = state.balance_info || {};
  const jarvis = state.jarvis_ai || {};
  const news = state.news || {};
  const profile = data.strategy_profile || {};
  const pos = state.active_position;
  const metrics = data.trade_metrics || {};
  const sysConfig = data.system_config || {};

  // 1. Navigation & 4-Coin Live Mark Prices Strip
  const navMode = document.getElementById("nav-mode");
  if (navMode) navMode.innerText = `${(state.mode || "DEMO").toUpperCase()} ONLINE`;
  const kpiSym = document.getElementById("kpi-symbol");
  if (kpiSym) kpiSym.innerText = state.symbol || activeSymbol;

  // Live 4-Coin Mark Prices (BTC, ETH, SOL, XRP)
  const radar = data.multi_asset_radar || {};
  ["BTC", "ETH", "SOL", "XRP"].forEach(coin => {
    const item = radar[coin] || {};
    const priceEl = document.getElementById(`cpc-price-${coin}`);
    const spreadEl = document.getElementById(`cpc-spread-${coin}`);
    const statusEl = document.getElementById(`cpc-status-${coin}`);
    const cardEl = document.getElementById(`cpc-${coin}`);
    
    if (priceEl && item.mark_price !== undefined) {
      const p = item.mark_price;
      priceEl.innerText = p < 2 ? `$${p.toFixed(4)}` : `$${p.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
    if (spreadEl && item.spread_pct !== undefined) {
      spreadEl.innerText = `${item.spread_pct.toFixed(3)}%`;
    }
    if (statusEl && cardEl) {
      if (item.is_active) {
        statusEl.innerText = "ACTIVE FOCUS";
        statusEl.style.color = "var(--cyan)";
        cardEl.classList.add("cpc-active");
        cardEl.classList.remove("cpc-top-hunt");
      } else if (item.is_top_pick) {
        statusEl.innerText = "TOP HUNT";
        statusEl.style.color = "var(--green)";
        cardEl.classList.add("cpc-top-hunt");
        cardEl.classList.remove("cpc-active");
      } else {
        statusEl.innerText = item.action || "SCANNING";
        statusEl.style.color = item.action === "BUY" ? "var(--green)" : (item.action === "SELL" ? "var(--red)" : "var(--text-dim)");
        cardEl.classList.remove("cpc-active");
        cardEl.classList.remove("cpc-top-hunt");
      }
    }
  });

  // Balance & Available Margin
  const balInr = bal.balance_inr !== undefined ? bal.balance_inr : 4155.24;
  const availInr = bal.available_margin_inr !== undefined ? bal.available_margin_inr : 4133.32;
  const balEl = document.getElementById("kpi-balance");
  if (balEl) balEl.innerText = `₹${balInr.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  
  const availEl = document.getElementById("kpi-avail-margin");
  if (availEl) {
    availEl.innerText = `₹${availInr.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  }

  // Cumulative Realized P&L & Win Rate
  const totPnl = metrics.total_pnl_inr || 0.0;
  const pnlEl = document.getElementById("kpi-realized-pnl");
  if (pnlEl) {
    pnlEl.innerText = `${totPnl >= 0 ? '+' : ''}₹${totPnl.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    pnlEl.style.color = totPnl >= 0 ? "var(--green)" : "var(--red)";
  }
  const winEl = document.getElementById("kpi-win-rate");
  if (winEl) {
    winEl.innerText = `${(metrics.win_rate_pct || 0).toFixed(1)}% (${metrics.wins || 0}W / ${metrics.losses || 0}L)`;
  }

  // Market Regime & Profile
  document.getElementById("kpi-regime").innerText = state.regime || "RANGING_CHOP";
  document.getElementById("kpi-profile").innerText = profile.mode || "RANGE_HARVESTER";

  // News Sentiment
  const sentLabel = news.sentiment_label || "NEUTRAL";
  const sentScore = news.sentiment_score !== undefined ? news.sentiment_score : 0.0;
  const sentEl = document.getElementById("kpi-sentiment-label");
  sentEl.innerText = sentLabel;
  sentEl.style.color = sentScore > 0 ? "var(--green)" : (sentScore < 0 ? "var(--red)" : "var(--cyan)");
  document.getElementById("kpi-sentiment-score").innerText = (sentScore >= 0 ? "+" : "") + sentScore.toFixed(2);

  // 2. Jarvis AI ("Jev AI") Brain
  const vBadge = document.getElementById("ai-verdict-badge");
  const verdict = jarvis.verdict || "NEUTRAL_HOLD";
  vBadge.innerText = verdict;
  vBadge.className = `verdict-tag verdict-${verdict.toLowerCase().replace('_', '-')}`;

  const qScore = jarvis.quant_score !== undefined ? jarvis.quant_score : 0;
  document.getElementById("ai-score-val").innerText = (qScore >= 0 ? "+" : "") + qScore;
  
  const barWidth = Math.max(5, Math.min(95, ((qScore + 100) / 200) * 100));
  document.getElementById("ai-score-bar").style.width = `${barWidth}%`;

  if (jarvis.summary) {
    document.getElementById("ai-rationale-text").innerText = jarvis.summary;
  }

  const aiEngineBadge = document.getElementById("ai-engine-badge");
  if (aiEngineBadge) {
    aiEngineBadge.innerText = jarvis.powered_by || "Quant Matrix Engine";
  }

  // 3. Active 100x Position Card
  const posCard = document.getElementById("position-card");
  const activeBody = document.getElementById("pos-active-body");
  const idleBody = document.getElementById("pos-idle-body");
  const posBadge = document.getElementById("pos-status-badge");

  if (pos) {
    posCard.classList.add("pos-active");
    activeBody.style.display = "block";
    idleBody.style.display = "none";

    posBadge.innerText = "OPEN IN MARKET";
    posBadge.className = "badge badge-live";

    const sideEl = document.getElementById("pos-side");
    sideEl.innerText = pos.side;
    sideEl.className = `badge ${pos.side === 'BUY' ? 'vote-buy' : 'vote-sell'}`;

    document.getElementById("pos-size-text").innerText = `${pos.contracts.toLocaleString()} Contracts (Margin: ₹${pos.margin_inr.toFixed(2)})`;
    
    const pnl = pos.unrealized_pnl_inr || 0.0;
    const roi = pos.margin_inr > 0 ? (pnl / pos.margin_inr) * 100 : 0.0;
    
    const posPnlEl = document.getElementById("pos-pnl");
    const posRoiEl = document.getElementById("pos-roi");
    
    posPnlEl.innerText = `${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(2)}`;
    posRoiEl.innerText = `(${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%)`;
    
    const pColor = pnl >= 0 ? "var(--green)" : "var(--red)";
    posPnlEl.style.color = pColor;
    posRoiEl.style.color = pColor;

    document.getElementById("pos-entry").innerText = `$${(pos.entry_price || 0).toFixed(4)}`;
    document.getElementById("pos-sl").innerText = `$${(pos.stop_loss || 0).toFixed(4)}`;
    document.getElementById("pos-tp").innerText = `$${(pos.take_profit || 0).toFixed(4)}`;
    document.getElementById("pos-liq").innerText = `$${(pos.liquidation_price || 0).toFixed(4)}`;

    const btnTest = document.getElementById("btn-test-scalp");
    const btnClose = document.getElementById("btn-close-pos");
    if (btnTest) btnTest.style.display = "none";
    if (btnClose) btnClose.style.display = "inline-flex";

    // Adaptive Bracket Tuning Display
    const adaptiveBox = document.getElementById("pos-adaptive-box");
    const adaptiveText = document.getElementById("pos-adaptive-text");
    const adjs = (data.adaptive_adjustments && data.adaptive_adjustments.length > 0) 
      ? data.adaptive_adjustments 
      : (pos.adaptive_adjustments || []);

    if (adaptiveBox && adaptiveText) {
      adaptiveBox.style.display = "flex";
      if (adjs.length > 0) {
        adaptiveText.innerText = adjs[adjs.length - 1];
      } else {
        adaptiveText.innerText = "Dynamic Trailing Stop & Orderbook Wall Front-Running Active";
      }
    }

  } else {
    posCard.classList.remove("pos-active");
    activeBody.style.display = "none";
    idleBody.style.display = "block";

    const adaptiveBox = document.getElementById("pos-adaptive-box");
    if (adaptiveBox) adaptiveBox.style.display = "none";

    posBadge.innerText = isAutoPilot ? "AUTONOMOUS SCANNING" : "AUTO-PILOT PAUSED";
    posBadge.className = "badge";
    posBadge.style.background = isAutoPilot ? "rgba(0, 242, 254, 0.15)" : "rgba(255,255,255,0.06)";
    posBadge.style.color = isAutoPilot ? "var(--cyan)" : "var(--text-dim)";

    const btnTest = document.getElementById("btn-test-scalp");
    const btnClose = document.getElementById("btn-close-pos");
    if (btnTest) btnTest.style.display = "inline-flex";
    if (btnClose) btnClose.style.display = "none";
  }

  // 3.5 Multi-Asset Quant Radar (BTC, ETH, SOL, XRP)
  if (data.multi_asset_radar) {
    renderMultiAssetRadar(data.multi_asset_radar, data.top_opportunity);
  }

  // 4. Bot Swarm Deliberation Matrix
  renderSwarmTable(data);

  // 4.5 Self-Learning Neural Brain & Dynamic Weights
  if (data.self_learning) {
    renderSelfLearning(data.self_learning);
  }

  // 5. Closed Trades Ledger
  renderTradesTable(metrics.trades || []);

  // 6. News Articles Feed
  if (news.articles && news.articles.length > 0) {
    renderNewsFeed(news.articles);
  }

  // 7. Auto-pilot button status sync
  if (sysConfig.auto_execution !== undefined) {
    isAutoPilot = sysConfig.auto_execution;
    updateAutoButtonUI(isAutoPilot);
  }

  // 7.5 IP Restriction banner alert
  const alertBanner = document.getElementById("ip-alert-banner");
  const ipText = document.getElementById("client-ip-text");
  if (alertBanner) {
    if (sysConfig.ip_restricted) {
      alertBanner.style.display = "block";
      if (ipText && sysConfig.detected_client_ip) {
        ipText.innerText = sysConfig.detected_client_ip;
      }
    } else {
      alertBanner.style.display = "none";
    }
  }

  // 8. Console Logging for new consensus
  if (data.candidate_signal && data.candidate_signal.rationale !== lastLogText) {
    addLog(`[CONSENSUS] ${data.candidate_signal.action} -> ${data.candidate_signal.rationale}`, "trade");
    lastLogText = data.candidate_signal.rationale;
  }
}

function renderSelfLearning(learning) {
  if (!learning) return;
  const countEl = document.getElementById("learning-trade-count");
  if (countEl) countEl.innerText = `${learning.total_trades_analyzed || 0} Trades Trained`;
  
  const winEl = document.getElementById("learning-win-rate");
  if (winEl) winEl.innerText = `${(learning.win_rate || 0).toFixed(1)}%`;

  const lessonEl = document.getElementById("learning-latest-lesson");
  if (lessonEl && learning.latest_reflection) {
    lessonEl.innerText = `"${learning.latest_reflection}"`;
  }

  const grid = document.getElementById("learning-weights-grid");
  if (grid && learning.bot_weights) {
    grid.innerHTML = Object.entries(learning.bot_weights).map(([bot, w]) => {
      const isHigh = w >= 1.1;
      const isLow = w < 0.9;
      const color = isHigh ? "var(--green)" : (isLow ? "var(--gold)" : "var(--cyan)");
      const bg = isHigh ? "rgba(34,197,94,0.12)" : (isLow ? "rgba(245,158,11,0.12)" : "rgba(0,242,254,0.08)");
      const border = isHigh ? "rgba(34,197,94,0.3)" : (isLow ? "rgba(245,158,11,0.3)" : "rgba(0,242,254,0.2)");
      const shortName = bot.replace(" Quantitative Brain", "").replace(" Scalper", "").replace(" Bot", "");
      return `
        <div style="background: ${bg}; border: 1px solid ${border}; border-radius: 6px; padding: 3px 8px; font-size: 0.75rem; display: flex; align-items: center; gap: 5px;">
          <span style="color: #cbd5e1;">${shortName}</span>
          <span class="mono" style="color: ${color}; font-weight: 700;">${w.toFixed(2)}x</span>
        </div>
      `;
    }).join("");
  }
}

function renderSwarmTable(data) {
  const tbody = document.getElementById("swarm-tbody");
  if (!tbody) return;

  const weights = (data.self_learning && data.self_learning.bot_weights) || {};

  const bots = [
    { name: "Market Analyst Bot", icon: "🌐", sig: data.analyst_signal },
    { name: "Liquidity Wick Sweep", icon: "🏹", sig: data.wick_signal },
    { name: "VWAP Pullback Sniper", icon: "🎯", sig: data.vwap_signal },
    { name: "Order Book Wall Scalper", icon: "🧱", sig: data.wall_signal },
    { name: "RSI Divergence", icon: "📐", sig: data.div_signal },
    { name: "Momentum Scalper", icon: "⚡", sig: data.mom_signal },
    { name: "Mean Reversion Bot", icon: "🌊", sig: data.mr_signal },
    { name: "News & Sentiment", icon: "📰", sig: data.news_signal },
    { name: "Jarvis AI Brain", icon: "🧠", sig: data.jarvis_signal },
    { 
      name: "Chief Risk Officer", 
      icon: "🛡️", 
      sig: { 
        action: data.risk_evaluation ? (data.risk_evaluation.approved ? "APPROVED" : "VETOED") : "STANDBY",
        confidence: 1.0,
        rationale: data.risk_evaluation ? data.risk_evaluation.rationale || data.risk_evaluation.reason : "Multi-bullet capital guardian active."
      } 
    }
  ];

  tbody.innerHTML = bots.map(b => {
    const act = (b.sig && b.sig.action) || "HOLD";
    let actClass = "vote-hold";
    if (act === "BUY" || act === "APPROVED") actClass = "vote-buy";
    if (act === "SELL" || act === "VETOED") actClass = "vote-sell";

    const conf = b.sig && b.sig.confidence !== undefined ? `${Math.round(b.sig.confidence * 100)}%` : "--";
    const rat = (b.sig && b.sig.rationale) || "Scanning market conditions...";
    const weightVal = weights[b.name] !== undefined ? weights[b.name] : (weights[b.name.replace(" Bot", "")] || null);
    const weightBadge = weightVal ? `<span class="badge" style="font-size: 0.65rem; margin-left: 6px; background: rgba(0,242,254,0.1); color: var(--cyan);">${weightVal.toFixed(2)}x</span>` : "";

    return `
      <tr>
        <td class="bot-name-cell"><span>${b.icon}</span> <span>${b.name}</span>${weightBadge}</td>
        <td><span class="vote-badge ${actClass}">${act}</span></td>
        <td class="mono" style="color: var(--cyan);">${conf}</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${rat}</td>
      </tr>
    `;
  }).join("");
}

function renderTradesTable(trades) {
  const tbody = document.getElementById("trades-tbody");
  const countBadge = document.getElementById("trade-count-badge");
  if (!tbody) return;

  if (countBadge) {
    countBadge.innerText = `${trades.length} Closed Trades`;
  }

  if (trades.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--text-dim); padding: 15px;">
          No closed trades recorded yet. Swarm is actively scanning...
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = trades.slice().reverse().map(t => {
    const pnl = t.pnl_inr || 0.0;
    const isWin = pnl >= 0;
    const pnlClass = isWin ? "vote-buy" : "vote-sell";
    const pnlColor = isWin ? "var(--green)" : "var(--red)";
    const sideClass = t.side === "BUY" ? "vote-buy" : "vote-sell";
    
    // Format timestamp
    let timeStr = "Recent";
    if (t.timestamp) {
      try {
        const d = new Date(t.timestamp);
        timeStr = d.toLocaleTimeString();
      } catch (e) {
        timeStr = t.timestamp.substring(11, 19);
      }
    }

    return `
      <tr>
        <td class="mono" style="color: var(--text-dim);">${timeStr}</td>
        <td><span class="vote-badge ${sideClass}">${t.side}</span></td>
        <td class="mono">${(t.contracts || 0).toLocaleString()}</td>
        <td class="mono">$${(t.exit_price || 0).toFixed(4)}</td>
        <td class="mono" style="color: ${pnlColor}; font-weight: 700;">
          ${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(2)}
        </td>
        <td>
          <span class="badge" style="background: rgba(255,255,255,0.06); font-size: 0.7rem; color: ${pnlColor};">
            ${t.reason || (isWin ? "PROFIT" : "STOPPED")}
          </span>
        </td>
      </tr>
    `;
  }).join("");
}

function renderNewsFeed(articles) {
  const container = document.getElementById("news-container");
  if (!container) return;

  container.innerHTML = articles.slice(0, 5).map(a => {
    const sent = a.sentiment || "NEUTRAL";
    const color = sent === "BULLISH" ? "var(--green)" : (sent === "BEARISH" ? "var(--red)" : "var(--text-dim)");

    return `
      <div class="news-item">
        <div class="news-meta">
          <span>${a.source || "CryptoFeed"} • ${a.time || "Recent"}</span>
          <span style="font-weight: 700; color: ${color}; font-size: 0.7rem;">[${sent}]</span>
        </div>
        <div class="news-title">${a.title}</div>
      </div>
    `;
  }).join("");
}

function addLog(msg, type = "info") {
  const box = document.getElementById("console-stream");
  if (!box) return;

  const now = new Date();
  const timeStr = now.toTimeString().split(" ")[0];
  const typeClass = type === "trade" ? "log-trade" : (type === "warn" ? "log-warn" : "log-info");

  const div = document.createElement("div");
  div.className = "log-entry";
  div.innerHTML = `
    <span class="log-time">[${timeStr}]</span>
    <span class="${typeClass}">${msg}</span>
  `;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function renderMultiAssetRadar(radar, topOpp) {
  const container = document.getElementById("radar-cards-grid");
  if (!container || !radar) return;

  const topCoinBadge = document.getElementById("radar-top-coin");
  const topActionBadge = document.getElementById("radar-top-action");
  if (topOpp && topCoinBadge && topActionBadge) {
    topCoinBadge.innerText = topOpp.coin || "XRP";
    topActionBadge.innerText = topOpp.action || "HOLD";
    topActionBadge.style.color = topOpp.action === 'BUY' ? 'var(--green)' : (topOpp.action === 'SELL' ? 'var(--red)' : 'var(--text-dim)');
  }

  const coins = ["BTC", "ETH", "SOL", "XRP"];
  let html = "";

  coins.forEach(coin => {
    const item = radar[coin] || {};
    const price = item.mark_price ? (item.mark_price < 2 ? `$${item.mark_price.toFixed(4)}` : `$${item.mark_price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`) : "---";
    const action = item.action || "HOLD";
    const conf = item.confidence ? `${(item.confidence * 100).toFixed(0)}%` : "50%";
    const jScore = item.jarvis_score !== undefined ? item.jarvis_score : 0;
    const jVerdict = item.jarvis_verdict || "NEUTRAL";
    const regime = item.regime || "RANGING_CHOP";
    const trigger = item.trigger_bot || "Scanning...";
    const isTop = item.is_top_pick;
    const isActive = item.is_active;

    let borderStyle = "1px solid rgba(255, 255, 255, 0.08)";
    let glow = "";
    if (isActive) {
      borderStyle = "1.5px solid var(--cyan)";
      glow = "box-shadow: 0 0 16px rgba(0, 242, 254, 0.3);";
    } else if (isTop) {
      borderStyle = "1.5px solid var(--green)";
      glow = "box-shadow: 0 0 16px rgba(34, 197, 94, 0.3);";
    }

    let actionClass = "vote-hold";
    if (action === "BUY") actionClass = "vote-buy";
    if (action === "SELL") actionClass = "vote-sell";

    const barWidth = Math.max(5, Math.min(100, ((jScore + 100) / 200) * 100));
    const barColor = jScore > 20 ? "var(--green)" : (jScore < -20 ? "var(--red)" : "var(--cyan)");

    html += `
      <div class="glass-card radar-coin-card" style="padding: 14px 16px; border-radius: 12px; border: ${borderStyle}; ${glow} background: rgba(15, 23, 42, 0.7); display: flex; flex-direction: column; gap: 8px; cursor: pointer; transition: all 0.2s;" onclick="switchAssetFocus('${coin}')">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-weight: 800; font-size: 1.05rem; color: #fff;">${coin}USD</span>
            ${isActive ? '<span class="badge" style="background: rgba(0,242,254,0.18); color: var(--cyan); font-size: 0.62rem; padding: 2px 6px;">ACTIVE</span>' : ''}
            ${isTop && !isActive ? '<span class="badge" style="background: rgba(34,197,94,0.18); color: var(--green); font-size: 0.62rem; padding: 2px 6px;">🏆 TOP HUNT</span>' : ''}
          </div>
          <span class="mono" style="font-size: 1.02rem; font-weight: 700; color: #fff;">${price}</span>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem;">
          <span style="color: var(--text-dim); font-size: 0.72rem;">${regime}</span>
          <span class="badge ${actionClass}" style="font-weight: 700; font-size: 0.72rem; padding: 2px 8px;">${action} ${conf}</span>
        </div>

        <div>
          <div style="display: flex; justify-content: space-between; font-size: 0.70rem; color: var(--text-dim); margin-bottom: 3px;">
            <span>AI Brain: <strong style="color: #fff;" class="mono">${jScore > 0 ? '+' : ''}${jScore}</strong></span>
            <span style="color: ${barColor}; font-weight: 600;">${jVerdict}</span>
          </div>
          <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden;">
            <div style="width: ${barWidth}%; height: 100%; background: ${barColor}; transition: width 0.3s;"></div>
          </div>
        </div>

        <div style="font-size: 0.72rem; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px; margin-top: 2px;">
          ⚡ <span style="color: #cbd5e1;">${trigger}</span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

window.switchAssetFocus = async function(coin) {
  document.querySelectorAll(".sym-btn").forEach(b => {
    if (b.dataset.symbol === coin) b.classList.add("active");
    else b.classList.remove("active");
  });
  activeSymbol = coin;
  try {
    await fetch("/api/set_symbol", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: coin })
    });
    addLog(`Manually focused radar on [${coin}]`, "info");
  } catch (err) {
    console.error("Error setting symbol:", err);
  }
};

