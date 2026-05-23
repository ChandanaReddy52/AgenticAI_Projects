/* ═══════════════════════════════════════════════
   ai.js — OpenAI API Integration

   All AI calls centralised here.
   Uses OpenAI Chat Completions API directly from
   the browser — no proxy needed.

   API key is loaded from js/config.js
   Model: gpt-4o-mini (configurable in config.js)

   Functions:
     callAI(prompt, opts)              — base call
     analyzeTicket(ticket)             — root cause + next steps
     suggestReply(ticket)              — draft customer reply
     suggestPriority(title,desc)       — JSON classification
     generateInsights(tickets)         — full queue (all tickets)
     generateTimelineInsights(t, win)  — timeline-windowed insights
     chatWithContext(msgs, ctx)        — conversational Q&A
   ═══════════════════════════════════════════════ */

'use strict';

function getKey() {
  const key = window.CONFIG?.OPENAI_API_KEY || '';
  if (!key || key === 'your-openai-api-key-here') {
    throw new Error('OpenAI API key not set. Open js/config.js and add your key.');
  }
  return key;
}

function getModel() {
  return window.CONFIG?.OPENAI_MODEL || 'gpt-4o-mini';
}

window.AI_API = {

  /* ──────────────────────────────────────────────
     BASE CALL
     ────────────────────────────────────────────── */

  async callAI(prompt, { systemPrompt, maxTokens = 1000 } = {}) {
    const messages = [];
    if (systemPrompt) messages.push({ role: 'system', content: systemPrompt });
    messages.push({ role: 'user', content: prompt });

    const body = {
      model:       getModel(),
      max_tokens:  maxTokens,
      messages,
      temperature: 0.3,
    };

    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${getKey()}`,
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error?.message || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    return data.choices?.[0]?.message?.content?.trim() || '';
  },

  /* ──────────────────────────────────────────────
     TICKET ANALYSIS
     ────────────────────────────────────────────── */

  async analyzeTicket(ticket) {
    const customer = window.getCustomer(ticket.customerId);

    const prompt = `Analyze this support ticket. Be direct and concise — 3 to 4 sentences max.
Cover: (1) root cause hypothesis, (2) business/severity impact, (3) recommended next steps.

Ticket ID: ${ticket.id}
Title: ${ticket.title}
Description: ${ticket.description}
Priority: ${ticket.priority}
Category: ${ticket.category}
Status: ${ticket.status}
Tags: ${ticket.tags.join(', ')}
Customer: ${customer
  ? `${customer.name} (${customer.industry}, ARR: $${(customer.arr/1000).toFixed(0)}K, Health: ${customer.health}/100)`
  : 'Unknown'}
SLA Due: ${ticket.due_date ? new Date(ticket.due_date).toLocaleDateString() : 'No SLA set'}

Start with the root cause. No preamble.`;

    return this.callAI(prompt);
  },

  /* ──────────────────────────────────────────────
     CUSTOMER REPLY DRAFT
     ────────────────────────────────────────────── */

  async suggestReply(ticket) {
    const prompt = `Draft a professional, empathetic customer-facing support reply. Max 80 words.
Include: acknowledgment, what we are doing to fix it, rough ETA.
No placeholders like [Name] or [Date].

Ticket: ${ticket.title}
Description: ${ticket.description}
Priority: ${ticket.priority}
Status: ${ticket.status}

Reply text only. No subject line, no preamble.`;

    return this.callAI(prompt);
  },

  /* ──────────────────────────────────────────────
     PRIORITY + CATEGORY SUGGESTION
     ────────────────────────────────────────────── */

  async suggestPriority(title, description) {
    const systemPrompt = `You are a support ticket classifier. Always respond with valid JSON only — no markdown, no backticks, no explanation.`;

    const prompt = `Classify this support ticket. Return ONLY this JSON:

{"priority":"critical|high|medium|low","category":"Bug|Feature Request|Feature Upgrade|Incident|Query","tags":["tag1","tag2","tag3"],"reason":"one sentence"}

Title: ${title}
Description: ${description}`;

    const raw = await this.callAI(prompt, { systemPrompt, maxTokens: 300 });
    try {
      return JSON.parse(raw.replace(/```(?:json)?```/g, '').trim());
    } catch {
      const match = raw.match(/\{[\s\S]*\}/);
      if (match) { try { return JSON.parse(match[0]); } catch { /* fall */ } }
      return null;
    }
  },

  /* ──────────────────────────────────────────────
     FULL QUEUE INSIGHTS (all tickets, legacy)
     ────────────────────────────────────────────── */

  async generateInsights(tickets) {
    return this.generateTimelineInsights(tickets, '7d');
  },

  /* ──────────────────────────────────────────────
     TIMELINE-WINDOWED INSIGHTS
     window: '7d' | '30d' | '90d'

     Each window has a distinct tone, filter scope,
     and narrative instruction baked into the prompt.
     The AI is told explicitly what story to tell:
       90d → neutral, scattered, no alarm
       30d → concern, signals forming, not urgent
       7d  → alert, convergence, action required
     ────────────────────────────────────────────── */

  async generateTimelineInsights(tickets, timeWindow) {

    // ── Filter tickets to the selected window ──
    const now = Date.now();
    const windowMs = timeWindow === '7d' ? 7 * 864e5
                   : timeWindow === '30d' ? 30 * 864e5
                   : 90 * 864e5;

    const filtered = tickets.filter(t => {
      const age = now - new Date(t.created_at).getTime();
      if (timeWindow === '7d')  return age <= 7 * 864e5;
      if (timeWindow === '30d') return age > 7 * 864e5 && age <= 30 * 864e5;
      if (timeWindow === '90d') return age > 30 * 864e5 && age <= 90 * 864e5;
      return true;
    });

    // ── Build per-ticket summary for the prompt ──
    const ticketSummary = filtered.map(t => {
      const cust = window.customers?.find(c => c.id === t.customerId);
      return {
        id:           t.id,
        title:        t.title,
        priority:     t.priority,
        status:       t.status,
        category:     t.category,
        tags:         t.tags,
        customer:     cust?.name || 'Unknown',
        arr:          cust ? `$${(cust.arr/1000).toFixed(0)}K` : 'Unknown',
        health:       cust?.health || 'Unknown',
        age_days:     Math.round((now - new Date(t.created_at).getTime()) / 864e5),
        key_comments: t.comments.slice(-2).map(c => `${c.author}: ${c.text.substring(0, 120)}`),
      };
    });

    // ── Window-specific tone and narrative instructions ──
    const toneInstructions = {
      '90d': `TONE: Neutral and observational. The system appears stable and healthy.
NARRATIVE: These tickets appear scattered and unrelated at first glance. Severity is low-to-medium. No single customer is raising alarms. However, subtly note that the 'sync' and 'offline' tags appear frequently — this is a weak signal worth monitoring.
IMPORTANT: Do NOT use urgent language. Do NOT mention systemic failure. Do NOT say "immediate action required". The story is: "everything looks normal — but there are early signals a trained eye might catch."
exec_summary tone: Calm, professional, reassuring. End with one subtle observation.
top_recommendation: Should be a light monitoring or process improvement suggestion — not a fix order.
patterns: Max 2 patterns. Low severity. Frame as "areas to watch" not "problems".
at_risk_customers: At most 1 customer flagged, with low urgency. Others described as "monitoring closely".
sla_at_risk: Empty array [] — no SLA urgency in this window.
sentiment_scores: Mostly neutral (3-5/10). At most one slightly elevated (6/10).`,

      '30d': `TONE: Concerned and attentive. Signals are emerging but not yet a crisis.
NARRATIVE: A pattern is becoming visible. Multiple tickets share the 'sync' and 'duplicate' tags. A finance team has flagged an anomaly but not escalated. One customer's WMS was initially blamed for something that may actually be an upstream sync issue. The root cause is not yet confirmed — investigation is ongoing.
IMPORTANT: Do NOT use panic language. Do NOT say "systemic failure" or "critical". Frame as: "pattern forming — warrants closer attention."
exec_summary tone: Measured concern. Acknowledge the trend without overstating severity.
top_recommendation: Should be a concrete investigation step — not emergency action.
patterns: 2-3 patterns. Medium severity. Emphasise that confirmation is still needed.
at_risk_customers: 1-2 customers with medium urgency. Frame as "at risk" not "churning".
sla_at_risk: 1-2 items maximum, framed as warnings not breaches.
sentiment_scores: Mix of neutral and concerned (4-7/10). No 9s or 10s.`,

      '7d': `TONE: Urgent but measured. Pattern has converged. Action is required — but this is not a total breakdown.
NARRATIVE: The signals from the previous month have converged into a confirmed pattern. Root cause is strongly suspected: missing idempotency on POST /api/orders. Two critical anchors: TKT-1002 (root cause identified) and TKT-1020 (VP formal escalation). Financial exposure is quantified at $67K. Two contract renewals are time-bound. A temporary workaround is in place but degrading productivity. QuickShip remains unaffected — the issue is not universal.
IMPORTANT: This is serious but solvable. Do NOT write as if the company is collapsing. Frame as: "approaching systemic failure — but one targeted fix addresses 80% of active issues."
exec_summary tone: Alert. Name the root cause. Quantify the impact. State the fix.
top_recommendation: Must name the specific fix: idempotency key on POST /api/orders.
patterns: 3-4 patterns. High severity. One must name the root cause explicitly.
at_risk_customers: 2-3 customers. GlobalFoods and FreshMart at high urgency with specific ARR at risk.
sla_at_risk: 3-4 items. Mix of breached and imminent.
sentiment_scores: Mostly frustrated-to-urgent (7-9/10). Reflect escalation language from comments.`,
    };

    const systemPrompt = `You are a support intelligence AI for a B2B supply chain platform. You analyze support ticket windows and return structured JSON insights. You always respond with ONLY valid JSON — no markdown, no backticks, no text before or after.`;

    const prompt = `Analyze this ${timeWindow === '7d' ? 'last 7 days' : timeWindow === '30d' ? 'last 30 days' : 'last quarter'} support ticket window.

${toneInstructions[timeWindow]}

Return ONLY valid JSON with this exact structure:
{
  "exec_summary": "2-3 sentences matching the tone instruction above",
  "top_recommendation": "one specific, actionable recommendation",
  "patterns": [
    {"title":"pattern name","description":"what you observed and why it matters","ticket_ids":["TKT-xxxx"],"severity":"critical|high|medium|low"}
  ],
  "at_risk_customers": [
    {"customer":"exact customer name from data","reason":"specific reason based on tickets","arr_at_risk":"amount","urgency":"critical|high|medium|low"}
  ],
  "sla_at_risk": [
    {"ticket_id":"TKT-xxxx","title":"short title","hours_left":-5,"action":"recommended action"}
  ],
  "sentiment_scores": [
    {"ticket_id":"TKT-xxxx","urgency_score":5,"sentiment":"frustrated|neutral|positive","signal":"key phrase from ticket"}
  ],
  "window": "${timeWindow}",
  "ticket_count": ${filtered.length}
}

Rules:
- hours_left must be NEGATIVE for breached SLAs
- Include ALL ${filtered.length} tickets in sentiment_scores
- Ticket IDs must exactly match: ${filtered.map(t => t.id).join(', ')}
- Follow the TONE and NARRATIVE instructions strictly

Ticket window data (${filtered.length} tickets):
${JSON.stringify(ticketSummary, null, 2)}`;

    const raw = await this.callAI(prompt, { systemPrompt, maxTokens: 3000 });

    try {
      return JSON.parse(raw.replace(/```(?:json)?|```/g, '').trim());
    } catch (e) {
      const match = raw.match(/\{[\s\S]*\}/);
      if (match) { try { return JSON.parse(match[0]); } catch { /* fall */ } }
      throw new Error('Could not parse timeline insights response.');
    }
  },

  /* ──────────────────────────────────────────────
     CONVERSATIONAL CHAT
     ────────────────────────────────────────────── */

  async chatWithContext(conversationHistory, ticketContext) {

    const systemContent = `You are a support intelligence assistant with full access to a ticket management system.
Help support leads understand their queue, identify patterns, and take action.
Be concise and data-driven. Reference ticket IDs like TKT-1001 when relevant.
Keep responses under 150 words unless more detail is needed.

System context:
${JSON.stringify(ticketContext, null, 2)}`;

    const messages = [
      { role: 'system', content: systemContent },
      ...conversationHistory,
    ];

    const body = {
      model:       getModel(),
      max_tokens:  600,
      temperature: 0.4,
      messages,
    };

    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${getKey()}`,
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error?.message || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    return data.choices?.[0]?.message?.content?.trim() || '';
  },
};
