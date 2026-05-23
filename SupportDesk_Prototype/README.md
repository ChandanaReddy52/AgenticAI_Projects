# SupportDesk — AI-Powered Customer Support Portal

A rapid prototype built for the DevRev Solutions Engineer assignment.
Demonstrates a production-grade support portal with AI-native architecture,
powered for ticket intelligence and DevRev-style conversational analytics.

---

## Live Demo

Open `index.html` directly in any browser — no build step, no server required.

> AI features (ticket analysis, insights, chat) require an OPENAI API key.
> Without a key the app is fully functional; AI panels show a graceful fallback message.

---

## Setup AI Features

1. Open js/config.js
2. Add:

window.CONFIG = {
  OPENAI_API_KEY: 'your-key',
  OPENAI_MODEL: 'model-of-your-choice'
};

---

## Features

### Core CRUD
- Create tickets with full enriched data model (priority, category, source, tags, SLA/due date)
- View all tickets with 5-dimension filtering (status, priority, category, source, search)
- Edit any ticket field inline via the Edit modal
- Ticket detail view with activity timeline

### Enriched Data Model
Every ticket carries:
| Field | Values |
|---|---|
| `priority` | critical / high / medium / low |
| `status` | open / in-progress / resolved / closed |
| `category` | Bug / Feature Request / Feature Upgrade / Incident / Query |
| `source` | Email / Chat / API / Manual |
| `tags` | Free-form array with chip UI |
| `due_date` | SLA deadline with live countdown |
| `customerId` | Links to Customer entity |
| `comments` | Internal thread with AI support |

### Customer Entity
- 5 enterprise customers with ARR, health score, industry, CSM
- Customer list with health bars and at-risk indicators
- Per-customer ticket history and AI churn risk assessment

### AI Features (Claude Sonnet 4)
1. **Ticket Analysis** — root cause hypothesis, severity, next steps
2. **Reply Drafting** — professional customer-facing reply in one click
3. **Auto-classify** — AI suggests priority, category, and tags on new ticket form
4. **AI Chat on Ticket Detail** — Internal & External conversational Q&A with full ticket + related-ticket context
5. **AI Insights Hub** — full queue analysis returning structured JSON:
   - Executive summary
   - Recurring issue pattern detection
   - Customer at-risk ranking
   - SLA breach predictions
   - Sentiment/urgency scoring per ticket
   - Conversational chat with entire queue as context

### Dashboard Analytics
- Chart.js line chart: ticket volume over last 7 days
- Chart.js doughnut: status distribution
- Priority breakdown bars
- At-risk customer widget
- AI queue summary

---

## Project Structure

```
supportdesk/
│
├── index.html                  # Entry point — all HTML structure
│
├── css/
│   ├── variables.css           # Design tokens (colours, spacing, radii)
│   ├── layout.css              # Sidebar, topbar, main area, grid
│   └── components.css          # All reusable UI components
│
├── js/
│   ├── data.js                 # Data model + seed data (Customer, Ticket)
│   ├── api.js                  # Simulated REST layer (getTickets, createTicket…)
│   ├── ui.js                   # Shared helpers: badges, toasts, SLA utils, stats
│   ├── config.js               # OPENAI API Key for AI layer
│   ├── ai.js                   # All Claude API calls (centralised)
│   ├── router.js               # Client-side SPA router (hash-based)
│   │
│   └── pages/
│       ├── dashboard.js        # Dashboard: charts, recent tickets, at-risk widget
│       ├── tickets.js          # Ticket list with multi-filter
│       ├── detail.js           # Ticket detail: edit, comments, AI chat
│       ├── newticket.js        # Create form with AI auto-classify
│       ├── customers.js        # Customer list + customer detail pages
│       ├── insights.js         # AI Insights Hub — the centrepiece
│       └── activity.js         # Activity feed
│
└── README.md
```

---

## Key Architectural Decisions

### 1. Module-Per-Concern JavaScript
Rather than one monolithic script, code is split into single-responsibility modules:
`data → api → ui → ai → router → pages`. This mirrors how a React/Vue app would be
structured with components. Each file can be opened independently to understand its role.
In the interview: *"If I were migrating this to React, each `pages/*.js` becomes a component,
`api.js` becomes a service layer, and `data.js` becomes a Zustand or Redux store."*

### 2. Simulated REST API Layer (`api.js`)
All data access flows through `API.getTickets()`, `API.createTicket()`, etc. — never by
directly mutating the `window.tickets` array from page code. The functions are async and
mirror real REST semantics (`GET /tickets`, `POST /tickets`, `PUT /tickets/:id`).
Swapping to a real backend (FastAPI/Express) requires changing exactly this one file.

### 3. Hash-Based Client-Side Router (`router.js`)
`Router.go('detail', 'TKT-1001')` updates the URL to `#detail/TKT-1001` and renders the
correct page without a reload. Browser back/forward work via `popstate`. Deep links are
shareable. This is the same mental model as React Router or Vue Router, without the build
toolchain.

### 4. AI as a Structured Data Layer (`ai.js`)
AI calls are prompted to return structured JSON wherever possible, not just prose.
`generateInsights()` returns `{ patterns, at_risk_customers, sla_at_risk, sentiment_scores }` —
each field drives a UI component. This is "AI-native architecture": Claude is treated as a
data API, not a text box. This directly mirrors what DevRev Computer does — indexing
structured data and making it queryable.

### 5. Enriched Data Model for AI Insight Quality
Every ticket carries `category`, `source`, `tags`, `customerId`, and `due_date`. This isn't
decoration — richer data means richer AI output. When Claude sees `tags: ['sync', 'ios',
'crash']` across 4 tickets, it can detect patterns. When it sees `customerId` with an
associated `arr: 840000` and `health: 42`, it can assess business risk. The data model is
deliberately designed to make the Insights Hub work well.

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| UI framework | Vanilla JS + HTML/CSS | No build step — instant demo, zero config |
| Charts | Chart.js 4.4 (CDN) | Industry standard, dark-mode friendly |
| AI | Claude Sonnet 4 (Anthropic API) | Best-in-class reasoning for structured output |
| Data store | In-memory JS arrays | Simulates REST API; swap to SQLite/Supabase trivially |
| Fonts | DM Sans + JetBrains Mono (Google Fonts) | Professional, readable, free |
| Routing | Custom hash router | SPA behaviour without React/Vue overhead |

---

## How to Add a Real Backend

1. Replace `js/api.js` functions with `fetch()` calls to your Express/FastAPI server
2. Change `window.tickets = []` in `data.js` to an initial empty state
3. The rest of the frontend is unchanged

Example swap in `api.js`:
```js
// Before (simulated)
async getTickets(filters) {
  return window.tickets.filter(...);
}

// After (real backend)
async getTickets(filters) {
  const params = new URLSearchParams(filters);
  const resp = await fetch(`/api/tickets?${params}`);
  return resp.json();
}
```

---

## AI Insights Hub — How It Works

The Insights Hub sends the full ticket queue (as structured JSON) to Claude with a
prompt requesting a specific JSON response schema:

```json
{
  "exec_summary": "...",
  "patterns": [{ "title", "description", "ticket_ids", "severity" }],
  "at_risk_customers": [{ "customer", "reason", "arr_at_risk", "urgency" }],
  "sla_at_risk": [{ "ticket_id", "title", "hours_left", "action" }],
  "sentiment_scores": [{ "ticket_id", "urgency_score", "sentiment", "signal" }],
  "top_recommendation": "..."
}
```

Each JSON field drives a dedicated UI component. The conversational chat interface
then uses the same ticket context as a system prompt, so follow-up questions like
*"When did the issue first appear?", "Which customer should I call first?"* are 
answered with full awareness of all tickets and customer health scores.

This architecture mirrors how DevRev Computer works: structured enterprise data
indexed and made conversationally queryable.
