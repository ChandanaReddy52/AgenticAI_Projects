/* ═══════════════════════════════════════════════
   pages/newticket.js — New Ticket Form
   ═══════════════════════════════════════════════ */

'use strict';

window.Pages = window.Pages || {};
window._newTags = [];

window.Pages.newTicket = function () {
  window._newTags = [];
  renderNewTagChips();
};

/* ── Tag Chip Management ── */
function renderNewTagChips() {
  const wrap = document.getElementById('new-tags-wrap');
  if (!wrap) return;
  const existingInput = wrap.querySelector('input');
  wrap.innerHTML = '';

  window._newTags.forEach((tag, i) => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.innerHTML = `${tag} <button class="tag-remove" onclick="window._newTags.splice(${i},1);renderNewTagChips()">×</button>`;
    wrap.appendChild(chip);
  });

  const inp = document.createElement('input');
  inp.placeholder = window._newTags.length ? 'Add more…' : 'Type tag + Enter…';
  inp.onkeydown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const v = inp.value.trim().replace(',', '');
      if (v && !window._newTags.includes(v)) { window._newTags.push(v); renderNewTagChips(); }
    }
  };
  if (existingInput) inp.focus();
  wrap.appendChild(inp);
}
window.renderNewTagChips = renderNewTagChips;

/* ── AI Priority Suggestion ── */
window.suggestPriority = async function () {
  const title = document.getElementById('new-title')?.value.trim();
  const desc  = document.getElementById('new-desc')?.value.trim();

  if (!desc) { UI.toast('Write a description first', 'error'); return; }

  const el = document.getElementById('ai-suggest-text');
  if (!el) return;

  // Hide placeholder, show result panel
  const placeholder = document.getElementById('ai-suggest-placeholder');
  if (placeholder) placeholder.style.display = 'none';

  UI.setLoading('ai-suggest-text', 'Analyzing with Claude...');
  el.style.display = 'block';

  try {
    const result = await AI_API.suggestPriority(title, desc);

    if (result) {
      el.innerHTML = `
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
          <span style="font-size:12px;color:var(--text3)">Suggested:</span>
          ${UI.priorityBadge(result.priority)}
          ${UI.categoryBadge(result.category)}
        </div>
        <div style="font-size:13px;color:var(--text2);margin-bottom:8px">${result.reason}</div>
        ${result.tags?.length ? `<div style="display:flex;gap:5px;flex-wrap:wrap">${result.tags.map(t=>`<span class="tag-chip">${t}</span>`).join('')}</div>` : ''}
        <div style="margin-top:10px;display:flex;gap:6px">
          <button class="btn btn-success btn-xs" onclick="applyAISuggestion(${JSON.stringify(result).replace(/"/g,'&quot;')})">✓ Apply suggestions</button>
        </div>`;

      // Set priority dropdown
      const priorityEl = document.getElementById('new-priority');
      if (priorityEl) priorityEl.value = result.priority;
    } else {
      el.textContent = 'Could not parse AI response.';
    }
  } catch (e) {
    el.innerHTML = '<span style="color:var(--text3);font-style:italic">AI unavailable.</span>';
  }
};

window.applyAISuggestion = function (result) {
  const priorityEl  = document.getElementById('new-priority');
  const categoryEl  = document.getElementById('new-category');
  if (priorityEl && result.priority)  priorityEl.value  = result.priority;
  if (categoryEl && result.category)  categoryEl.value  = result.category;

  // Merge suggested tags
  if (result.tags) {
    result.tags.forEach(t => { if (!window._newTags.includes(t)) window._newTags.push(t); });
    renderNewTagChips();
  }

  UI.toast('AI suggestions applied', 'success');
};

/* ── Create Ticket ── */
window.createTicket = async function () {
  const title    = document.getElementById('new-title')?.value.trim();
  const desc     = document.getElementById('new-desc')?.value.trim();
  const priority = document.getElementById('new-priority')?.value;
  const category = document.getElementById('new-category')?.value;
  const source   = 'Manual';  // auto-populated; source field removed from UI
  const assignee = document.getElementById('new-assignee')?.value;
  const customer = document.getElementById('new-customer')?.value;
  const dueDate  = document.getElementById('new-due-date')?.value;

  if (!title)  { UI.toast('Title is required', 'error'); return; }
  if (!desc)   { UI.toast('Description is required', 'error'); return; }

  try {
    const ticket = await API.createTicket({
      title, description: desc,
      priority, category, source, assignee,
      customerId: customer || null,
      tags: window._newTags,
      due_date: dueDate ? new Date(dueDate).toISOString() : null,
    });

    UI.updateStats();
    UI.toast(`Ticket ${ticket.id} created`, 'success');
    Router.go('detail', ticket.id);
  } catch (e) {
    UI.toast('Failed to create ticket: ' + e.message, 'error');
  }
};
