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
  startClock();
  startPolling();
});

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

  // 1. Navigation & KPIs
  document.getElementById("nav-mode").innerText = `${(state.mode || "DEMO").toUpperCase()} ONLINE`;
  document.getElementById("kpi-symbol").innerText = state.symbol || activeSymbol;
  document.getElementById("kpi-price").innerText = `$${(state.mark_price || 0).toFixed(4)}`;
  document.getElementById("kpi-spread").innerText = `${(ob.spread_pct || 0).toFixed(3)}%`;

  // Balance & Available Margin
  const balInr = bal.balance_inr !== undefined ? bal.balance_inr : 68975.30;
  const availInr = bal.available_margin_inr !== undefined ? bal.available_margin_inr : 23079.61;
  document.getElementById("kpi-balance").innerText = `₹${balInr.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  
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

  // 4. Bot Swarm Deliberation Matrix
  renderSwarmTable(data);

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

  // 8. Console Logging for new consensus
  if (data.candidate_signal && data.candidate_signal.rationale !== lastLogText) {
    addLog(`[CONSENSUS] ${data.candidate_signal.action} -> ${data.candidate_signal.rationale}`, "trade");
    lastLogText = data.candidate_signal.rationale;
  }
}

function renderSwarmTable(data) {
  const tbody = document.getElementById("swarm-tbody");
  if (!tbody) return;

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

    return `
      <tr>
        <td class="bot-name-cell"><span>${b.icon}</span> <span>${b.name}</span></td>
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
