/* ═══════════════════════════════════════════════
   pages/insights.js — AI Insights Hub
   Timeline-aware: Quarter → Month → Week

   Architecture:
     - Timeline selector (toggle) filters ticket window
     - Each window calls generateTimelineInsights()
       with distinct tone/narrative prompt
     - Results cached per window to avoid re-calling AI
       on re-selection of the same window
     - Conversational chat always has full context
   ═══════════════════════════════════════════════ */

'use strict';

window.Pages = window.Pages || {};

/* ── State ── */
let _insightsChatHistory = [];
let _insightsContext     = null;
let _currentWindow       = '7d';         // active timeline window
let _windowCache         = {};           // cache: { '7d': insights, '30d': insights, '90d': insights }
let _allTickets          = [];
let _allCustomers        = [];

/* ── Window config ── */
const WINDOWS = {
  '7d':  { label: 'Last 7 Days',   tone: 'alert',   toneLabel: 'Alert',   toneColor: 'var(--red)',    toneDesc: 'Pattern convergence — action required' },
  '30d': { label: 'Last 30 Days',  tone: 'concern', toneLabel: 'Concern', toneColor: 'var(--amber)',  toneDesc: 'Signals emerging — monitor closely' },
  '90d': { label: 'Last Quarter',  tone: 'neutral', toneLabel: 'Stable',  toneColor: 'var(--green)',  toneDesc: 'Background noise — system appears healthy' },
};

/* ──────────────────────────────────────────────
   PAGE ENTRY POINT
   ────────────────────────────────────────────── */

window.Pages.insights = async function () {
  _insightsChatHistory = [];
  _windowCache = {};   // clear cache on page load

  const [tickets, customers] = await Promise.all([API.getTickets(), API.getCustomers()]);
  _allTickets   = tickets;
  _allCustomers = customers;
  _insightsContext = { tickets, customers };

  renderInsightsShell();
  await loadWindow(_currentWindow);
};

/* ──────────────────────────────────────────────
   SHELL — renders the static frame (selector +
   content area + chat). Only called once per visit.
   ────────────────────────────────────────────── */

function renderInsightsShell() {
  const page = document.getElementById('page-insights');
  if (!page) return;

  // Replace the topbar subtitle area content
  page.innerHTML = `

    <!-- ── TIMELINE SELECTOR ── -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
      <div>
        <div style="font-size:13px;color:var(--text2)">Claude analyzes your ticket queue through three time lenses to surface early signals before they become incidents.</div>
      </div>
      <div style="display:flex;align-items:center;gap:0">
        ${Object.entries(WINDOWS).map(([key, cfg]) => `
          <button
            id="win-btn-${key}"
            class="timeline-btn ${key === _currentWindow ? 'active' : ''}"
            onclick="switchWindow('${key}')"
            style="
              padding:7px 16px;
              font-size:12.5px;
              font-weight:500;
              font-family:var(--font);
              cursor:pointer;
              border:1px solid var(--border2);
              background:${key === _currentWindow ? 'var(--accent)' : 'var(--surface)'};
              color:${key === _currentWindow ? 'white' : 'var(--text2)'};
              border-radius:${key==='7d'?'var(--radius-sm) 0 0 var(--radius-sm)':key==='90d'?'0 var(--radius-sm) var(--radius-sm) 0':'0'};
              border-left-width:${key==='30d'||key==='90d'?'0':'1px'};
              transition:all 0.15s;
              white-space:nowrap;
            "
          >${cfg.label}</button>
        `).join('')}
      </div>
    </div>

    <!-- ── TONE INDICATOR ── -->
    <div id="tone-indicator" style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:18px">
      <div id="tone-dot" style="width:8px;height:8px;border-radius:50%;background:var(--green);flex-shrink:0"></div>
      <span id="tone-label" style="font-size:12px;font-weight:600;color:var(--green)">Stable</span>
      <span style="color:var(--border2);font-size:12px">|</span>
      <span id="tone-desc" style="font-size:12px;color:var(--text2)">Background noise — system appears healthy</span>
      <span style="margin-left:auto;font-size:11px;color:var(--text3);font-family:var(--mono)" id="window-meta"></span>
    </div>

    <!-- ── DYNAMIC CONTENT AREA ── -->
    <div id="insights-content"></div>

    <!-- ── CONVERSATIONAL CHAT (always visible) ── -->
    <div class="ai-panel" style="margin-top:16px" id="insights-chat-panel">
      <div class="ai-panel-header">
        <div class="ai-icon"><svg viewBox="0 0 12 12"><path d="M6 1l1.5 3 3.5.5-2.5 2.5.6 3.5L6 9l-3.1 1.5.6-3.5L1 4.5l3.5-.5L6 1z"/></svg></div>
        <span class="ai-panel-title">Ask the Insights AI</span>
        <span class="ai-panel-sub" id="chat-context-label">Full context · all windows</span>
      </div>
      <div class="ai-chat">
        <div class="ai-chat-messages" id="insights-chat-messages">
          <div class="ai-msg bot">
            <div class="ai-msg-avatar" style="background:linear-gradient(135deg,#4f7fff,#a78bfa)">✦</div>
            <div class="ai-msg-bubble">I have full context of all 24 tickets across three time windows. Ask me anything — early signals, root cause, which customer to call first, or what one fix delivers the most impact.</div>
          </div>
          <div style="padding:6px 0;display:flex;gap:6px;flex-wrap:wrap" id="suggested-questions-row"></div>
        </div>
        <div class="ai-chat-input-row">
          <input type="text" id="insights-chat-input" placeholder="e.g. When did the sync issue first appear?" onkeydown="if(event.key==='Enter') sendInsightsChat()">
          <button class="btn btn-primary btn-sm" onclick="sendInsightsChat()">↑</button>
        </div>
      </div>
    </div>
  `;

  updateToneIndicator(_currentWindow);
  renderSuggestedQuestions();
}

/* ──────────────────────────────────────────────
   WINDOW SWITCH
   ────────────────────────────────────────────── */

window.switchWindow = async function(win) {
  if (win === _currentWindow && _windowCache[win]) return;
  _currentWindow = win;

  // Update button states
  Object.keys(WINDOWS).forEach(k => {
    const btn = document.getElementById(`win-btn-${k}`);
    if (!btn) return;
    btn.style.background = k === win ? 'var(--accent)' : 'var(--surface)';
    btn.style.color      = k === win ? 'white' : 'var(--text2)';
  });

  updateToneIndicator(win);
  await loadWindow(win);
};

/* ──────────────────────────────────────────────
   LOAD WINDOW — fetch AI insights for the
   selected time window, use cache if available
   ────────────────────────────────────────────── */

async function loadWindow(win) {
  const contentEl = document.getElementById('insights-content');
  if (!contentEl) return;

  // Show skeleton
  contentEl.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:14px">
      ${[1,2,3].map(() => `
      <div class="card" style="opacity:0.45">
        <div class="ai-loading"><div class="ai-dot"></div><div class="ai-dot"></div><div class="ai-dot"></div>
        <span style="font-size:12px;color:var(--text3);margin-left:8px">Analyzing ${WINDOWS[win].label.toLowerCase()}…</span>
        </div>
      </div>`).join('')}
    </div>`;

  // Use cache if available
  if (_windowCache[win]) {
    renderInsightsResults(_windowCache[win], win);
    return;
  }

  try {
    const insights = await AI_API.generateTimelineInsights(_allTickets, win);
    _windowCache[win] = insights;
    renderInsightsResults(insights, win);
  } catch (e) {
    contentEl.innerHTML = `
      <div class="card" style="padding:24px;text-align:center">
        <div style="font-size:13px;color:var(--red);margin-bottom:6px">AI analysis failed</div>
        <div style="font-size:12px;color:var(--text3)">${e.message}</div>
        <button class="btn btn-ghost btn-sm" style="margin-top:12px" onclick="loadWindow('${win}')">↻ Retry</button>
      </div>`;
  }
}

/* ──────────────────────────────────────────────
   TONE INDICATOR
   ────────────────────────────────────────────── */

function updateToneIndicator(win) {
  const cfg = WINDOWS[win];
  const dot   = document.getElementById('tone-dot');
  const label = document.getElementById('tone-label');
  const desc  = document.getElementById('tone-desc');
  const meta  = document.getElementById('window-meta');

  if (dot)   dot.style.background   = cfg.toneColor;
  if (label) { label.style.color    = cfg.toneColor; label.textContent = cfg.toneLabel; }
  if (desc)  desc.textContent        = cfg.toneDesc;

  // Count tickets in window
  const now = Date.now();
  const count = _allTickets.filter(t => {
    const age = now - new Date(t.created_at).getTime();
    if (win === '7d')  return age <= 7 * 864e5;
    if (win === '30d') return age > 7 * 864e5 && age <= 30 * 864e5;
    if (win === '90d') return age > 30 * 864e5 && age <= 90 * 864e5;
  }).length;

  if (meta) meta.textContent = `${count} tickets · GPT-4o-mini`;
}

/* ──────────────────────────────────────────────
   RENDER INSIGHTS — builds the full panel grid
   from AI response. Tone-aware styling.
   ────────────────────────────────────────────── */

function renderInsightsResults(insights, win) {
  const el = document.getElementById('insights-content');
  if (!el) return;

  const cfg = WINDOWS[win];
  const accentColor  = cfg.toneColor;
  const accentBorder = win === '7d' ? 'var(--red-border)' : win === '30d' ? 'var(--amber-border)' : 'var(--green-border)';
  const accentBg     = win === '7d' ? 'rgba(255,92,92,0.06)' : win === '30d' ? 'rgba(245,166,35,0.06)' : 'rgba(45,212,160,0.06)';

  el.innerHTML = `

    <!-- EXEC SUMMARY -->
    <div style="background:${accentBg};border:1px solid ${accentBorder};border-radius:var(--radius);padding:16px 20px;margin-bottom:18px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
        <div class="ai-icon"><svg viewBox="0 0 12 12"><path d="M6 1l1.5 3 3.5.5-2.5 2.5.6 3.5L6 9l-3.1 1.5.6-3.5L1 4.5l3.5-.5L6 1z"/></svg></div>
        <span style="font-size:13px;font-weight:600">Executive Summary</span>
        <span style="font-size:10.5px;font-weight:500;padding:2px 8px;border-radius:20px;background:${accentBg};color:${accentColor};border:1px solid ${accentBorder}">${cfg.toneLabel}</span>
        <span style="font-size:10px;color:var(--text3);font-family:var(--mono);margin-left:auto">${new Date().toLocaleTimeString()}</span>
      </div>
      <p style="font-size:14px;color:var(--text);line-height:1.75;margin-bottom:${insights.top_recommendation?'12px':'0'}">${insights.exec_summary || '—'}</p>
      ${insights.top_recommendation ? `
      <div style="padding:10px 12px;background:var(--surface2);border:1px solid var(--border2);border-left:3px solid ${accentColor};border-radius:0 var(--radius-sm) var(--radius-sm) 0">
        <span style="font-size:10.5px;color:${accentColor};font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Top Recommendation</span>
        <p style="font-size:13px;color:var(--text2);margin-top:4px;line-height:1.6">${insights.top_recommendation}</p>
      </div>` : ''}
    </div>

    <!-- PATTERNS + AT-RISK GRID -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
      <div class="card">
        <div class="card-title">${win === '7d' ? '🔴' : win === '30d' ? '🟡' : '🟢'} Recurring Patterns</div>
        ${renderPatterns(insights.patterns || [], win)}
      </div>
      <div class="card">
        <div class="card-title">⚠ Customer Risk</div>
        ${renderAtRisk(insights.at_risk_customers || [], win)}
      </div>
    </div>

    <!-- SLA + SENTIMENT GRID -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
      <div class="card">
        <div class="card-title">⏱ SLA Predictions</div>
        ${renderSLARisk(insights.sla_at_risk || [], win)}
      </div>
      <div class="card">
        <div class="card-title">🌡 Urgency & Sentiment</div>
        ${renderSentiment(insights.sentiment_scores || [])}
      </div>
    </div>
  `;
}

/* ──────────────────────────────────────────────
   SECTION RENDERERS
   ────────────────────────────────────────────── */

function renderPatterns(patterns, win) {
  if (!patterns.length) {
    const msg = win === '90d'
      ? 'No clear patterns detected — system appears stable.'
      : 'Pattern analysis pending.';
    return `<p style="font-size:13px;color:var(--text3);font-style:italic">${msg}</p>`;
  }

  return patterns.map(p => `
  <div class="insight-card" style="margin-bottom:10px">
    <div class="insight-title">
      <div class="insight-severity sev-${p.severity || 'medium'}"></div>
      <span style="font-size:13px;font-weight:500">${p.title}</span>
      <span style="margin-left:auto;font-size:10.5px;padding:1px 7px;border-radius:20px;background:var(--surface3);color:var(--text3);text-transform:capitalize">${p.severity || 'medium'}</span>
    </div>
    <div class="insight-body" style="margin-top:5px">${p.description}</div>
    ${p.ticket_ids?.length ? `
    <div class="insight-meta" style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px">
      ${p.ticket_ids.map(id => `<span style="font-family:var(--mono);font-size:10.5px;color:var(--accent);cursor:pointer;padding:1px 5px;background:var(--accent-dim);border-radius:3px" onclick="Router.go('detail','${id}')">${id}</span>`).join('')}
    </div>` : ''}
  </div>`).join('');
}

function renderAtRisk(atRisk, win) {
  if (!atRisk.length) {
    return `<p style="font-size:13px;color:var(--text3);font-style:italic">No customers flagged at risk in this window.</p>`;
  }

  const urgencyColor = { critical: 'var(--red)', high: 'var(--amber)', medium: 'var(--accent)', low: 'var(--green)' };

  return atRisk.map(r => {
    const customer = _allCustomers.find(c => c.name === r.customer);
    const hl = customer ? UI.healthLabel(customer.health) : { color: 'var(--text2)', label: 'Unknown' };
    const uColor = urgencyColor[r.urgency] || 'var(--amber)';

    return `
    <div class="insight-card" style="cursor:pointer;margin-bottom:10px" onclick="${customer ? `Router.go('customer','${customer.id}')` : ''}">
      <div class="insight-title">
        <div class="insight-severity sev-${r.urgency || 'medium'}"></div>
        <span style="font-size:13px;font-weight:500">${r.customer}</span>
        <span style="margin-left:auto;font-size:11px;color:${uColor};font-weight:500">${r.urgency || 'medium'}</span>
      </div>
      <div class="insight-body" style="margin-top:5px">${r.reason}</div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:6px">
        ${r.arr_at_risk ? `<span style="font-family:var(--mono);font-size:11px;color:var(--text3)">ARR: ${r.arr_at_risk}</span>` : ''}
        ${customer ? `<div style="flex:1;max-width:80px">
          <div class="health-bar"><div class="health-fill ${UI.healthColor(customer.health)}" style="width:${customer.health}%"></div></div>
        </div>
        <span style="font-size:11px;color:${hl.color}">${hl.label}</span>` : ''}
      </div>
    </div>`;
  }).join('');
}

function renderSLARisk(slaRisk, win) {
  if (!slaRisk.length) {
    const msg = win === '90d'
      ? 'No SLA concerns in this window — within normal thresholds.'
      : 'No active SLA breaches detected.';
    return `<p style="font-size:13px;color:var(--text3);font-style:italic">${msg}</p>`;
  }

  return slaRisk.map(s => {
    const breached = s.hours_left < 0;
    const borderColor = breached ? 'var(--red)' : 'var(--amber)';
    const labelClass  = breached ? 'sla-breached' : 'sla-warning';
    const hoursAbs = Math.abs(Math.ceil(s.hours_left || 0));
    const timeLabel = breached ? `${hoursAbs}h overdue` : `${hoursAbs}h left`;

    return `
    <div class="insight-card" style="cursor:pointer;border-left:2px solid ${borderColor};padding-left:12px;margin-bottom:8px"
         onclick="Router.go('detail','${s.ticket_id}')">
      <div class="insight-title">
        <span class="ticket-id">${s.ticket_id}</span>
        <span class="${labelClass}" style="margin-left:auto;font-size:11px">${timeLabel}</span>
      </div>
      <div class="insight-body" style="font-size:12px;margin-top:3px">${s.title || '—'}</div>
      ${s.action ? `<div class="insight-meta" style="margin-top:4px;font-size:11px">→ ${s.action}</div>` : ''}
    </div>`;
  }).join('');
}

function renderSentiment(scores) {
  if (!scores.length) return `<p style="font-size:13px;color:var(--text3);font-style:italic">No sentiment data available.</p>`;

  const sorted = [...scores].sort((a, b) => (b.urgency_score || 0) - (a.urgency_score || 0));
  const sentColor = { frustrated: 'var(--red)', neutral: 'var(--text2)', positive: 'var(--green)' };

  return sorted.slice(0, 8).map(s => {
    const score = Math.min(10, Math.max(1, s.urgency_score || 5));
    const color = sentColor[s.sentiment] || 'var(--text2)';
    const barColor = score >= 8 ? 'var(--red)' : score >= 6 ? 'var(--amber)' : 'var(--green)';

    return `
    <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer"
         onclick="Router.go('detail','${s.ticket_id}')">
      <span class="ticket-id" style="min-width:78px;font-size:11px">${s.ticket_id}</span>
      <div style="flex:1;min-width:0">
        <div style="height:3px;background:var(--surface3);border-radius:2px;overflow:hidden;margin-bottom:3px">
          <div style="height:100%;width:${score*10}%;background:${barColor};border-radius:2px;transition:width 0.4s"></div>
        </div>
        <div style="font-size:10.5px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.signal || ''}</div>
      </div>
      <span style="font-size:10.5px;color:${color};white-space:nowrap;text-transform:capitalize;min-width:60px;text-align:right">${s.sentiment} ${score}/10</span>
    </div>`;
  }).join('');
}

/* ──────────────────────────────────────────────
   SUGGESTED QUESTIONS — window-aware
   ────────────────────────────────────────────── */

function renderSuggestedQuestions() {
  const el = document.getElementById('suggested-questions-row');
  if (!el) return;

  const questions = [
    'When did the sync issue first appear as a signal?',
    'Which one fix would resolve the most active issues?',
    'Which customer should we call first and why?',
    'How has the duplicate order rate changed over time?',
  ];

  el.innerHTML = questions.map(q =>
    `<div class="ai-chip" onclick="askSuggested('${q.replace(/'/g, "\\'")}')">${q}</div>`
  ).join('');
}

window.askSuggested = function(q) {
  const input = document.getElementById('insights-chat-input');
  if (input) { input.value = q; sendInsightsChat(); }
};

/* ──────────────────────────────────────────────
   CONVERSATIONAL CHAT
   ────────────────────────────────────────────── */

window.sendInsightsChat = async function() {
  const input = document.getElementById('insights-chat-input');
  const text  = input?.value.trim();
  if (!text) return;
  input.value = '';

  const messages = document.getElementById('insights-chat-messages');
  if (!messages) return;

  // User bubble
  messages.innerHTML += `
  <div class="ai-msg user">
    <div class="ai-msg-avatar" style="background:var(--surface3);color:var(--text2);font-size:10px">You</div>
    <div class="ai-msg-bubble">${text}</div>
  </div>`;

  // Typing indicator
  const typingId = `typing-${Date.now()}`;
  messages.innerHTML += `
  <div id="${typingId}" class="ai-msg bot">
    <div class="ai-msg-avatar" style="background:linear-gradient(135deg,#4f7fff,#a78bfa)">✦</div>
    <div class="ai-msg-bubble"><div class="ai-loading"><div class="ai-dot"></div><div class="ai-dot"></div><div class="ai-dot"></div></div></div>
  </div>`;
  messages.scrollTop = messages.scrollHeight;

  _insightsChatHistory.push({ role: 'user', content: text });

  try {
    // Give chat full context — all windows + cached insights
    const context = {
      ..._insightsContext,
      current_window: _currentWindow,
      cached_insights: _windowCache,
    };

    const reply = await AI_API.chatWithContext(_insightsChatHistory, context);
    _insightsChatHistory.push({ role: 'assistant', content: reply });

    document.getElementById(typingId)?.remove();
    messages.innerHTML += `
    <div class="ai-msg bot">
      <div class="ai-msg-avatar" style="background:linear-gradient(135deg,#4f7fff,#a78bfa)">✦</div>
      <div class="ai-msg-bubble">${reply.replace(/\n/g, '<br>')}</div>
    </div>`;
    messages.scrollTop = messages.scrollHeight;

  } catch (e) {
    document.getElementById(typingId)?.remove();
    messages.innerHTML += `
    <div class="ai-msg bot">
      <div class="ai-msg-avatar" style="background:var(--surface3)">✦</div>
      <div class="ai-msg-bubble" style="color:var(--text3)">AI unavailable: ${e.message}</div>
    </div>`;
  }
};

/* ── Refresh (topbar button) ── */
window.refreshInsights = function() {
  _windowCache = {};
  window.Pages.insights();
};
