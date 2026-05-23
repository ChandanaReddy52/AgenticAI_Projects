/* ═══════════════════════════════════════════════
   pages/customers.js — Customers + Detail Pages
   ═══════════════════════════════════════════════ */

'use strict';

window.Pages = window.Pages || {};

window.Pages.customers = async function () {
  const customers = await API.getCustomers();
  const tickets   = await API.getTickets();
  renderCustomerList(customers, tickets);
};

function renderCustomerList(customers, tickets) {
  const el = document.getElementById('customers-list');
  if (!el) return;

  el.innerHTML = customers.map(c => {
    const cTickets  = tickets.filter(t => t.customerId === c.id);
    const openCount = cTickets.filter(t => t.status === 'open' || t.status === 'in-progress').length;
    const critCount = cTickets.filter(t => t.priority === 'critical' && t.status !== 'resolved' && t.status !== 'closed').length;
    const hl        = UI.healthLabel(c.health);
    const slaBreached = cTickets.filter(t => {
      if (!t.due_date || t.status === 'resolved' || t.status === 'closed') return false;
      return new Date(t.due_date) < Date.now();
    }).length;

    return `
    <div class="card" style="cursor:pointer;transition:border var(--t-fast)"
         onmouseenter="this.style.borderColor='var(--border3)'"
         onmouseleave="this.style.borderColor=''"
         onclick="Router.go('customer','${c.id}')">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
        <div style="display:flex;align-items:center;gap:12px">
          <div class="avatar avatar-lg">${c.name.split(' ').map(w=>w[0]).join('').slice(0,2)}</div>
          <div>
            <div style="font-size:14px;font-weight:600">${c.name}</div>
            <div style="font-size:12px;color:var(--text3)">${c.industry} · ${c.plan} · Since ${new Date(c.since).getFullYear()}</div>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:18px;font-weight:600;font-family:var(--mono);color:var(--text)">${UI.formatARR(c.arr)}</div>
          <div style="font-size:11px;color:var(--text3)">ARR</div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)">
        ${statPill('Health', `<span style="color:${hl.color};font-weight:600">${c.health}/100</span>`)}
        ${statPill('Open Tickets', `<span style="font-family:var(--mono);font-size:15px">${openCount}</span>`)}
        ${statPill('Critical', `<span style="font-family:var(--mono);font-size:15px;color:${critCount>0?'var(--red)':'var(--text)'}">${critCount}</span>`)}
        ${statPill('SLA Breached', `<span style="font-family:var(--mono);font-size:15px;color:${slaBreached>0?'var(--amber)':'var(--text)'}">${slaBreached}</span>`)}
      </div>

      <div style="margin-top:10px">
        <div style="font-size:11px;color:var(--text3);margin-bottom:4px">Customer Health</div>
        <div class="health-bar">
          <div class="health-fill ${UI.healthColor(c.health)}" style="width:${c.health}%"></div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function statPill(label, valueHTML) {
  return `<div style="background:var(--surface2);padding:8px 10px;border-radius:var(--radius-sm)">
    <div style="font-size:10.5px;color:var(--text3);text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px">${label}</div>
    <div>${valueHTML}</div>
  </div>`;
}

/* ── Customer Detail Page ── */
window.Pages.customerDetail = async function (id) {
  const customer = await API.getCustomer(id);
  if (!customer) { Router.go('customers'); return; }

  const cTickets = await API.getCustomerTickets(id);
  renderCustomerDetail(customer, cTickets);
};

function renderCustomerDetail(customer, tickets) {
  const el = document.getElementById('customer-detail-content');
  if (!el) return;

  const hl         = UI.healthLabel(customer.health);
  const openTix    = tickets.filter(t => t.status === 'open' || t.status === 'in-progress');
  const resolvedTix = tickets.filter(t => t.status === 'resolved' || t.status === 'closed');

  el.innerHTML = `
    <div>
      <!-- Header -->
      <div class="card" style="margin-bottom:14px">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px">
          <div class="avatar avatar-lg" style="width:48px;height:48px;font-size:16px">${customer.name.split(' ').map(w=>w[0]).join('').slice(0,2)}</div>
          <div>
            <div style="font-size:17px;font-weight:700">${customer.name}</div>
            <div style="font-size:12px;color:var(--text3)">${customer.industry} · ${customer.plan} Plan · Customer since ${new Date(customer.since).getFullYear()}</div>
          </div>
          <div style="margin-left:auto;text-align:right">
            <div style="font-size:22px;font-weight:700;font-family:var(--mono)">${UI.formatARR(customer.arr)}</div>
            <div style="font-size:11px;color:var(--text3)">Annual Recurring Revenue</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">
          ${statPill('Health Score', `<span style="color:${hl.color};font-weight:600;font-size:16px">${customer.health}/100 — ${hl.label}</span>`)}
          ${statPill('CSM', `<span style="font-size:13px">${customer.csm}</span>`)}
          ${statPill('Contact', `<span style="font-size:12px">${customer.contact}</span>`)}
        </div>

        <div class="health-bar" style="margin-bottom:14px">
          <div class="health-fill ${UI.healthColor(customer.health)}" style="width:${customer.health}%"></div>
        </div>

        <button class="btn btn-ghost btn-sm" onclick="Router.go('customers')">← All Customers</button>
      </div>

      <!-- Tickets -->
      <div class="card">
        <div class="card-title">Open Tickets (${openTix.length})</div>
        ${openTix.length === 0
          ? '<p style="font-size:13px;color:var(--text3)">No open tickets ✓</p>'
          : openTix.map(t => `
          <div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--border);cursor:pointer"
               onclick="Router.go('detail','${t.id}')">
            <span class="ticket-id">${t.id}</span>
            <span style="flex:1;font-size:13px;color:var(--text)">${t.title.substring(0,60)}…</span>
            ${UI.priorityBadge(t.priority)}
            ${UI.statusBadge(t.status)}
          </div>`).join('')}
      </div>
    </div>

    <div>
      <!-- AI Risk Panel -->
      <div class="ai-panel" style="margin-bottom:14px">
        <div class="ai-panel-header">
          <div class="ai-icon"><svg viewBox="0 0 12 12"><path d="M6 1l1.5 3 3.5.5-2.5 2.5.6 3.5L6 9l-3.1 1.5.6-3.5L1 4.5l3.5-.5L6 1z"/></svg></div>
          <span class="ai-panel-title">Customer Risk Analysis</span>
        </div>
        <div class="ai-panel-body">
          <div class="ai-response" id="customer-ai-text" style="color:var(--text3);font-style:italic">Analyzing…</div>
        </div>
      </div>

      <!-- Stats Sidebar -->
      <div class="card">
        <div class="card-title">Ticket Summary</div>
        ${statPill('Total Tickets',  `<span style="font-family:var(--mono)">${tickets.length}</span>`)}
        <div style="height:8px"></div>
        ${statPill('Resolved',       `<span style="font-family:var(--mono);color:var(--green)">${resolvedTix.length}</span>`)}
        <div style="height:8px"></div>
        ${statPill('Avg Priority',   `<span style="font-size:12px">${topPriority(tickets)}</span>`)}
      </div>
    </div>
  `;

  runCustomerAI(customer, tickets);
}

function topPriority(tickets) {
  if (!tickets.length) return '—';
  const order = { critical: 4, high: 3, medium: 2, low: 1 };
  const top = tickets.reduce((a, b) => (order[b.priority] || 0) > (order[a.priority] || 0) ? b : a, tickets[0]);
  return UI.priorityBadge(top.priority);
}

async function runCustomerAI(customer, tickets) {
  try {
    const openCritical = tickets.filter(t => t.priority === 'critical' && t.status !== 'resolved').length;
    const result = await AI_API.callAI(
      `Analyze this customer account in 2-3 sentences. Assess churn risk, recommend next CSM action.

Customer: ${customer.name}
ARR: $${(customer.arr/1000).toFixed(0)}K
Health: ${customer.health}/100
Open Tickets: ${tickets.filter(t=>t.status==='open'||t.status==='in-progress').length}
Critical Open: ${openCritical}
Top Issues: ${tickets.slice(0,3).map(t=>t.title).join(' | ')}

Be direct. Start with risk level.`,
      { maxTokens: 200 }
    );
    UI.setText('customer-ai-text', result, { italic: false, color: 'var(--text2)' });
  } catch (e) {
    UI.setText('customer-ai-text', 'AI unavailable.', { italic: true });
  }
}
