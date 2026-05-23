/* ═══════════════════════════════════════════════
   pages/tickets.js — Ticket List Page
   ═══════════════════════════════════════════════ */

'use strict';

window.Pages = window.Pages || {};

window.Pages.tickets = async function () {
  await renderTicketList();
};

async function renderTicketList() {
  const search   = document.getElementById('filter-search')?.value   || '';
  const status   = document.getElementById('filter-status')?.value   || '';
  const priority = document.getElementById('filter-priority')?.value || '';
  const category = document.getElementById('filter-category')?.value || '';
  const source   = document.getElementById('filter-source')?.value   || '';

  const tickets = await API.getTickets({ status, priority, category, source, search });
  const tbody   = document.getElementById('tickets-table');
  if (!tbody) return;

  if (!tickets.length) {
    tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><p>No tickets match your filters.</p></div></td></tr>';
    return;
  }

  tbody.innerHTML = tickets.map(t => {
    const customer = window.getCustomer(t.customerId);
    const sla      = UI.slaStatus(t.due_date);
    return `
    <tr onclick="Router.go('detail','${t.id}')">
      <td><span class="ticket-id">${t.id}</span></td>
      <td style="max-width:260px">
        <div class="ticket-title">${t.title}</div>
        <div class="ticket-desc">${t.description}</div>
        <div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">
          ${t.tags.slice(0,3).map(tg => `<span class="tag-chip">${tg}</span>`).join('')}
        </div>
      </td>
      <td>${UI.categoryBadge(t.category)}</td>
      <td>${UI.priorityBadge(t.priority)}</td>
      <td>${UI.statusBadge(t.status)}</td>
      <td>${UI.sourceBadge(t.source)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:6px">
          <div class="avatar avatar-sm">${t.assignee.split(' ').map(w=>w[0]).join('').slice(0,2)}</div>
          <span style="font-size:12px;color:var(--text2)">${t.assignee.split(' ')[0]}</span>
        </div>
      </td>
      <td>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px">
          <span class="${sla.cls}">${sla.label}</span>
          <span style="font-size:10.5px;color:var(--text3);font-family:var(--mono)">${UI.timeAgo(t.created_at)}</span>
        </div>
      </td>
    </tr>`;
  }).join('');
}

/* Called by filter inputs (oninput / onchange) */
window.filterTickets = function () {
  renderTicketList();
};
