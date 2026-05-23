/* ═══════════════════════════════════════════════════════════════
   agent_api.js — SupportDesk Agent Bridge
   Location: supportdesk/js/agent_api.js

   Drop-in replacement for the AI_API calls in js/ai.js.
   When the Python agent server is running (localhost:8000),
   this file intercepts all 5 AI_API functions and routes them
   to the agent instead of calling OpenAI directly.

   HOW TO ACTIVATE:
   Add this ONE line to index.html, after ai.js:
     <script src="js/agent_api.js"></script>

   HOW TO DEACTIVATE:
   Remove that script tag — js/ai.js takes over again.
   No other files need to change.

   WHAT CHANGES:
   Before:  Browser → OpenAI API (raw LLM, no tools, no RAG)
   After:   Browser → Python Agent (5 tools + ChromaDB + memory + adaptation)

   The /api/insights endpoint is the main upgrade:
     Before: Single LLM call with all tickets in prompt
     After:  detect_patterns + rank_customer_risk (deterministic) +
             predict_sla_risk + cross_ticket_analysis (RAG 12 docs)
             → Structured, grounded, tool-verified output
═══════════════════════════════════════════════════════════════ */

'use strict';

const AGENT_API_URL = 'http://localhost:8000';

/* ── Health check on load ──────────────────────────────────────── */

async function _checkAgentHealth() {
  try {
    const resp = await fetch(`${AGENT_API_URL}/api/health`, { method: 'GET' });
    if (resp.ok) {
      const data = await resp.json();
      console.log(`[Agent Bridge] Connected — status: ${data.status} | ${data.agent}`);
      return true;
    }
  } catch (e) {
    console.warn('[Agent Bridge] Agent server not reachable at', AGENT_API_URL);
    console.warn('[Agent Bridge] Falling back to direct OpenAI calls (js/ai.js)');
    return false;
  }
}

async function _post(endpoint, body) {
  const resp = await fetch(`${AGENT_API_URL}${endpoint}`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

/* ════════════════════════════════════════════════════════════════
   OVERRIDE AI_API — replaces the 5 functions from js/ai.js
   Only overrides if the agent server responds to health check.
════════════════════════════════════════════════════════════════ */

_checkAgentHealth().then(agentAvailable => {
  if (!agentAvailable) return;   // keep original AI_API from ai.js

  console.log('[Agent Bridge] Patching AI_API with agent endpoints...');

  /* ── 1. analyzeTicket ──────────────────────────────────────── */
  AI_API.analyzeTicket = async function(ticket) {
    const data = await _post('/api/analyze-ticket', { ticket });
    return data.result;
    // data.structured contains the full agent JSON if needed
  };

  /* ── 2. suggestReply ───────────────────────────────────────── */
  AI_API.suggestReply = async function(ticket) {
    const data = await _post('/api/suggest-reply', { ticket });
    return data.result;
  };

  /* ── 3. suggestPriority ────────────────────────────────────── */
  AI_API.suggestPriority = async function(title, description) {
    return _post('/api/suggest-priority', { title, description });
    // Returns { priority, category, tags, reason } directly
  };

  /* ── 4. generateInsights (main upgrade) ────────────────────── */
  AI_API.generateInsights = async function(tickets) {
    return AI_API.generateTimelineInsights(tickets, '7d');
  };

  AI_API.generateTimelineInsights = async function(tickets, window) {
    const data = await _post('/api/insights', { tickets, window });
    // Agent adds _agent_latency_ms and _source for observability
    if (data._agent_latency_ms) {
      console.log(`[Agent Bridge] Insights (${window}) — ${data._agent_latency_ms}ms`);
    }
    return data;
  };

  /* ── 5. chatWithContext ─────────────────────────────────────── */
  AI_API.chatWithContext = async function(conversationHistory, context) {
    const data = await _post('/api/chat', {
      history: conversationHistory,
      context,
      query: conversationHistory.at(-1)?.content || '',
    });
    return data.result;
  };

  console.log('[Agent Bridge] AI_API patched — all calls now routed through Python agent');
  console.log('[Agent Bridge] Tools active: analyze_ticket · detect_patterns · rank_customer_risk · predict_sla_risk · cross_ticket_analysis');
});
