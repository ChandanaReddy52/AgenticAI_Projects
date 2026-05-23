/* ═══════════════════════════════════════════════
   pages/dashboard.js — Dashboard Page
   ═══════════════════════════════════════════════ */

'use strict';

window.Pages = window.Pages || {};

window.Pages.dashboard = async function () {
  const tickets   = await API.getTickets();
  const customers = await API.getCustomers();

  renderRecentTable(tickets.slice(0, 6));
  renderPriorityBars(tickets);
  renderCharts(tickets);
  renderAtRiskCustomers(customers, tickets);

  // AI overview if tickets exist
  if (tickets.length > 0) runDashboardAI(tickets);
};

/* ── Recent Tickets Table ── */
function renderRecentTable(tickets) {
  const tbody = document.getElementById('dash-table');
  if (!tbody) return;

  if (!tickets.length) {
    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No tickets yet.</p></div></td></tr>';
    return;
  }

  tbody.innerHTML = tickets.map(t => {
    const sla = UI.slaStatus(t.due_date);
    return `
    <tr onclick="Router.go('detail','${t.id}')">
      <td><span class="ticket-id">${t.id}</span></td>
      <td>
        <div class="ticket-title">${t.title.substring(0, 55)}${t.title.length > 55 ? '…' : ''}</div>
        <div style="display:flex;gap:5px;margin-top:3px">${UI.categoryBadge(t.category)}</div>
      </td>
      <td>${UI.priorityBadge(t.priority)}</td>
      <td>${UI.statusBadge(t.status)}</td>
      <td><span class="${sla.cls}">${sla.label}</span></td>
    </tr>`;
  }).join('');
}

/* ── Priority Breakdown Bars ── */
function renderPriorityBars(tickets) {
  const el = document.getElementById('priority-bars');
  if (!el) return;

  const levels  = ['critical', 'high', 'medium', 'low'];
  const colors  = { critical: 'var(--red)', high: 'var(--amber)', medium: 'var(--accent)', low: 'var(--green)' };
  const total   = tickets.length || 1;

  el.innerHTML = levels.map(lvl => {
    const count = tickets.filter(t => t.priority === lvl).length;
    const pct   = Math.round((count / total) * 100);
    return `
    <div style="margin-bottom:11px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
        <span style="text-transform:capitalize;color:var(--text2)">${lvl}</span>
        <span style="font-family:var(--mono);color:var(--text3)">${count}</span>
      </div>
      <div style="height:4px;background:var(--surface3);border-radius:2px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${colors[lvl]};border-radius:2px;transition:width 0.6s ease"></div>
      </div>
    </div>`;
  }).join('');
}

/* ── Charts (Chart.js) ── */
function renderCharts(tickets) {
  renderStatusDonut(tickets);
  renderVolumeChart(tickets);
}

function renderStatusDonut(tickets) {
  const canvas = document.getElementById('chart-donut');
  if (!canvas) return;

  // Destroy previous instance
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  const counts = {
    Open:         tickets.filter(t => t.status === 'open').length,
    'In Progress':tickets.filter(t => t.status === 'in-progress').length,
    Resolved:     tickets.filter(t => t.status === 'resolved').length,
    Closed:       tickets.filter(t => t.status === 'closed').length,
  };

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: Object.keys(counts),
      datasets: [{
        data: Object.values(counts),
        backgroundColor: ['#4f7fff', '#f5a623', '#2dd4a0', '#363d52'],
        borderColor: '#13161e',
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#8a90a2', font: { size: 11, family: 'DM Sans' }, padding: 12, boxWidth: 10 },
        },
        tooltip: {
          backgroundColor: '#1f2430',
          titleColor: '#e8eaf0',
          bodyColor: '#8a90a2',
          borderColor: 'rgba(255,255,255,0.12)',
          borderWidth: 1,
        },
      },
    },
  });
}

function renderVolumeChart(tickets) {
  const canvas = document.getElementById('chart-volume');
  if (!canvas) return;

  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  // Group by day (last 7 days)
  const days   = [];
  const counts = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const dayStr = d.toDateString();
    days.push(label);
    counts.push(tickets.filter(t => new Date(t.created_at).toDateString() === dayStr).length);
  }

  new Chart(canvas, {
    type: 'line',
    data: {
      labels: days,
      datasets: [{
        label: 'Tickets Created',
        data: counts,
        borderColor: '#4f7fff',
        backgroundColor: 'rgba(79,127,255,0.08)',
        pointBackgroundColor: '#4f7fff',
        pointRadius: 4,
        pointHoverRadius: 6,
        borderWidth: 2,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1f2430',
          titleColor: '#e8eaf0',
          bodyColor: '#8a90a2',
          borderColor: 'rgba(255,255,255,0.12)',
          borderWidth: 1,
        },
      },
      scales: {
        x: { ticks: { color: '#555b6e', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: {
          ticks: { color: '#555b6e', font: { size: 11 }, stepSize: 1 },
          grid:  { color: 'rgba(255,255,255,0.04)' },
          beginAtZero: true,
        },
      },
    },
  });
}

/* ── At-Risk Customers Widget ── */
function renderAtRiskCustomers(customers, tickets) {
  const el = document.getElementById('at-risk-list');
  if (!el) return;

  const atRisk = customers
    .filter(c => c.health < 65)
    .map(c => {
      const openCritical = tickets.filter(t => t.customerId === c.id && t.priority === 'critical' && t.status !== 'resolved' && t.status !== 'closed').length;
      return { ...c, openCritical };
    })
    .sort((a, b) => a.health - b.health);

  if (!atRisk.length) {
    el.innerHTML = '<p style="font-size:13px;color:var(--text3)">All customers healthy ✓</p>';
    return;
  }

  el.innerHTML = atRisk.map(c => {
    const hl = UI.healthLabel(c.health);
    return `
    <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);cursor:pointer"
         onclick="Router.go('customer','${c.id}')">
      <div style="flex:1;min-width:0">
        <div style="font-size:13px;font-weight:500;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${c.name}</div>
        <div style="font-size:11px;color:var(--text3)">${UI.formatARR(c.arr)} ARR · ${c.openCritical} critical open</div>
        <div class="health-bar" style="width:100%;margin-top:4px">
          <div class="health-fill ${UI.healthColor(c.health)}" style="width:${c.health}%"></div>
        </div>
      </div>
      <span style="font-size:12px;font-weight:500;color:${hl.color};white-space:nowrap">${hl.label}</span>
    </div>`;
  }).join('');
}

/* ── Dashboard AI Overview ── */
async function runDashboardAI(tickets) {
  const el = document.getElementById('ai-overview-text');
  const actEl = document.getElementById('ai-overview-actions');
  if (!el) return;

  UI.setLoading('ai-overview-text', 'Analyzing with Claude...');

  try {
    const summary = tickets.slice(0, 10).map(t =>
      `${t.id}: ${t.title} [${t.priority}/${t.status}/${t.category}]`
    ).join('\n');

    const result = await AI_API.callAI(
      `You are a support ops AI. Analyze this ticket queue in 2-3 sentences: highlight the most critical issue, any pattern you see, and one urgent recommendation.\n\n${summary}`,
      { maxTokens: 200 }
    );

    UI.setText('ai-overview-text', result, { italic: false, color: 'var(--text2)' });
    if (actEl) actEl.style.display = 'flex';
  } catch (e) {
    UI.setText('ai-overview-text', 'AI insights unavailable.', { italic: true });
  }
}
