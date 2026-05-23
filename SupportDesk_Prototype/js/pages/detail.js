/* ═══════════════════════════════════════════════
   pages/detail.js — Ticket Detail Page
   ═══════════════════════════════════════════════ */
'use strict';

window.Pages = window.Pages || {};
let _currentTicketId = null;
let _chatHistory = [];

window.Pages.detail = async function (id) {
  if (!id) { Router.go('tickets'); return; }
  _currentTicketId = id;
  _chatHistory = [];
  const ticket = await API.getTicket(id);
  if (!ticket) { UI.toast('Ticket not found', 'error'); Router.go('tickets'); return; }
  renderDetailPage(ticket);
  triggerAIAnalysis(ticket);
};

/* classify a comment as internal or external */
function isExternal(c) {
  const a = c.author || '';
  return (
    a.includes('Customer') || a.includes('VP') || a.includes('COO') ||
    a.includes('CFO') || a.includes('Compliance') || a.includes('Marcus') ||
    a.includes('Priya') || a.includes('Okafor') || a.includes('Laura') ||
    a.includes('Ananya') || a.includes('System Monitor') || a.includes('Platform')
  );
}

function renderDetailPage(ticket) {
  const customer = window.getCustomer(ticket.customerId);
  const sla = UI.slaStatus(ticket.due_date);
  const container = document.getElementById('detail-content');
  if (!container) return;

  const internalComments = ticket.comments.filter(c => !isExternal(c));
  const externalComments = ticket.comments.filter(c => isExternal(c));

  container.innerHTML = `
    <!-- LEFT -->
    <div>
      <!-- Header Card -->
      <div class="card" style="margin-bottom:14px">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:14px">
          <div style="flex:1">
            <div style="font-size:11px;color:var(--text3);font-family:var(--mono);margin-bottom:3px">${ticket.id}</div>
            <div style="font-size:16px;font-weight:600;line-height:1.4;color:var(--text)">${ticket.title}</div>
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
            ${UI.priorityBadge(ticket.priority)}
            ${UI.statusBadge(ticket.status)}
            ${UI.categoryBadge(ticket.category)}
          </div>
        </div>
        <div style="font-size:13.5px;color:var(--text2);line-height:1.7;background:var(--surface2);padding:14px;border-radius:var(--radius-sm);margin-bottom:14px">${ticket.description}</div>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;flex-wrap:wrap">
          <span style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:0.6px">Tags:</span>
          <div style="display:flex;gap:5px;flex-wrap:wrap">${UI.tagChips(ticket.tags)}</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding-top:14px;border-top:1px solid var(--border)">
          ${metaField('Assignee', `<div style="display:flex;align-items:center;gap:6px"><div class="avatar avatar-sm">${ticket.assignee.split(' ').map(w=>w[0]).join('').slice(0,2)}</div><span style="font-size:13px">${ticket.assignee}</span></div>`)}
          ${metaField('Customer', customer ? `<span style="cursor:pointer;color:var(--accent);font-size:13px" onclick="Router.go('customer','${customer.id}')">${customer.name}</span>` : '<span style="color:var(--text3)">—</span>')}
          ${metaField('Created', `<span style="font-family:var(--mono);font-size:12px">${UI.formatDate(ticket.created_at)}</span>`)}
          ${metaField('SLA / Due', `<span class="${sla.cls}">${sla.label}</span>${ticket.due_date ? `<br><span style="font-size:10.5px;color:var(--text3);font-family:var(--mono)">${UI.formatDate(ticket.due_date)}</span>` : ''}`)}
        </div>
        <div style="display:flex;gap:8px;margin-top:14px;padding-top:12px;border-top:1px solid var(--border);flex-wrap:wrap">
          <button class="btn btn-primary btn-sm" onclick="openEditModal()">✏ Edit Ticket</button>
          <button class="btn btn-ghost btn-sm" onclick="Router.go('tickets')">← Back</button>
          ${customer && customer.health < 50 ? `<span style="display:inline-flex;align-items:center;gap:5px;padding:4px 10px;background:var(--red-dim);color:var(--red);border:1px solid var(--red-border);border-radius:var(--radius-sm);font-size:12px">⚠ Customer At Risk</span>` : ''}
        </div>
      </div>

      <!-- Comments: Internal / External Tabs -->
      <div class="card" style="margin-bottom:14px">
        <!-- Tab bar -->
        <div style="display:flex;gap:0;margin-bottom:14px;border-bottom:1px solid var(--border)">
          <button id="tab-internal" onclick="switchCommentTab('internal')"
            style="padding:8px 16px;font-size:12.5px;font-weight:500;font-family:var(--font);border:none;border-bottom:2px solid var(--accent);background:none;color:var(--accent);cursor:pointer">
            🔒 Internal (${internalComments.length})
          </button>
          <button id="tab-external" onclick="switchCommentTab('external')"
            style="padding:8px 16px;font-size:12.5px;font-weight:500;font-family:var(--font);border:none;border-bottom:2px solid transparent;background:none;color:var(--text3);cursor:pointer">
            💬 External (${externalComments.length})
          </button>
        </div>

        <!-- Internal tab -->
        <div id="comments-panel-internal">
          <div id="comments-internal">
            ${renderCommentList(internalComments, 'No internal notes yet.')}
          </div>
          <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <textarea id="reply-internal" placeholder="Add internal note…"
              style="width:100%;background:var(--surface2);border:1px solid var(--border2);color:var(--text);padding:9px 12px;border-radius:var(--radius-sm);font-family:var(--font);font-size:13px;outline:none;resize:vertical;min-height:68px;margin-bottom:8px"></textarea>
            <div style="display:flex;gap:8px">
              <button class="btn btn-primary btn-sm" onclick="postTabComment('internal')">Post Note</button>
              <button class="btn btn-ghost btn-sm" onclick="generateDraft('internal')">✦ AI Draft</button>
            </div>
            <div id="ai-draft-internal" style="display:none;margin-top:10px;padding:10px 12px;background:var(--accent-dim);border:1px solid var(--accent-glow);border-radius:var(--radius-sm);font-size:13px;color:var(--text2);line-height:1.6;white-space:pre-wrap"></div>
          </div>
        </div>

        <!-- External tab -->
        <div id="comments-panel-external" style="display:none">
          <div id="comments-external">
            ${renderCommentList(externalComments, 'No customer messages yet.')}
          </div>
          <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <textarea id="reply-external" placeholder="Write customer reply…"
              style="width:100%;background:var(--surface2);border:1px solid var(--border2);color:var(--text);padding:9px 12px;border-radius:var(--radius-sm);font-family:var(--font);font-size:13px;outline:none;resize:vertical;min-height:68px;margin-bottom:8px"></textarea>
            <div style="display:flex;gap:8px">
              <button class="btn btn-primary btn-sm" onclick="postTabComment('external')">Send Reply</button>
              <button class="btn btn-ghost btn-sm" onclick="generateDraft('external')">✦ AI Draft</button>
            </div>
            <div id="ai-draft-external" style="display:none;margin-top:10px;padding:10px 12px;background:var(--accent-dim);border:1px solid var(--accent-glow);border-radius:var(--radius-sm);font-size:13px;color:var(--text2);line-height:1.6;white-space:pre-wrap"></div>
          </div>
        </div>
      </div>

      <!-- Timeline -->
      <div class="card">
        <div class="card-title">📋 Activity Timeline</div>
        <div>
          ${ticket.timeline.map(e => `
          <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div>
              <div class="timeline-action">${e.action}</div>
              <div class="timeline-time">${new Date(e.time).toLocaleString()} · ${e.author}</div>
            </div>
          </div>`).join('')}
        </div>
      </div>
    </div>

    <!-- RIGHT -->
    <div>
      <div class="ai-panel" style="margin-bottom:14px">
        <div class="ai-panel-header">
          <div class="ai-icon"><svg viewBox="0 0 12 12"><path d="M6 1l1.5 3 3.5.5-2.5 2.5.6 3.5L6 9l-3.1 1.5.6-3.5L1 4.5l3.5-.5L6 1z"/></svg></div>
          <span class="ai-panel-title">AI Analysis</span>
          <span class="ai-panel-sub">OpenAI</span>
        </div>
        <div class="ai-panel-body">
          <div class="ai-response" id="ai-detail-response" style="color:var(--text3);font-style:italic">Analyzing…</div>
          <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
            <div class="ai-chip" onclick="triggerAIAnalysis(null)">↻ Re-analyze</div>
            <div class="ai-chip" onclick="draftReply()">Draft reply</div>
          </div>
        </div>
      </div>

      <div class="ai-panel" style="margin-bottom:14px">
        <div class="ai-panel-header">
          <div class="ai-icon"><svg viewBox="0 0 12 12"><path d="M6 1l1.5 3 3.5.5-2.5 2.5.6 3.5L6 9l-3.1 1.5.6-3.5L1 4.5l3.5-.5L6 1z"/></svg></div>
          <span class="ai-panel-title">Ask AI about this ticket</span>
        </div>
        <div class="ai-chat">
          <div class="ai-chat-messages" id="detail-chat-messages">
            <div class="ai-msg bot">
              <div class="ai-msg-avatar" style="background:linear-gradient(135deg,#4f7fff,#a78bfa)">✦</div>
              <div class="ai-msg-bubble">Ask me anything about this ticket — root cause, related issues, escalation advice, or a customer reply draft.</div>
            </div>
          </div>
          <div class="ai-chat-input-row">
            <input type="text" id="detail-chat-input" placeholder="e.g. Is this related to any other tickets?" onkeydown="if(event.key==='Enter') sendDetailChat()">
            <button class="btn btn-primary btn-sm" onclick="sendDetailChat()">↑</button>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Ticket Info</div>
        ${metaField('Ticket ID', `<span style="font-family:var(--mono);font-size:12px;color:var(--accent)">${ticket.id}</span>`)}
        ${metaField('Status', UI.statusBadge(ticket.status))}
        ${metaField('Priority', UI.priorityBadge(ticket.priority))}
        ${metaField('Category', UI.categoryBadge(ticket.category))}
        ${metaField('Source', UI.sourceBadge(ticket.source))}
        ${customer ? `
        <hr class="divider">
        <div class="detail-field">
          <div class="detail-key">Customer Health</div>
          <div style="display:flex;align-items:center;gap:8px;margin-top:4px">
            <div class="health-bar" style="flex:1"><div class="health-fill ${UI.healthColor(customer.health)}" style="width:${customer.health}%"></div></div>
            <span style="font-size:12px;font-weight:500;color:${UI.healthLabel(customer.health).color}">${customer.health}/100</span>
          </div>
        </div>
        <div class="detail-field">
          <div class="detail-key">ARR</div>
          <div class="detail-value" style="font-family:var(--mono)">${UI.formatARR(customer.arr)}</div>
        </div>` : ''}
      </div>
    </div>
  `;
}

function metaField(key, valueHTML) {
  return `<div class="detail-field"><div class="detail-key">${key}</div><div class="detail-value">${valueHTML}</div></div>`;
}

function renderCommentList(comments, emptyMsg) {
  if (!comments.length) return `<div style="padding:8px 0;color:var(--text3);font-size:13px">${emptyMsg}</div>`;
  return comments.map(c => `
  <div class="comment-item">
    <div class="avatar avatar-sm">${c.author.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()}</div>
    <div class="comment-body">
      <div class="comment-meta">
        <span class="comment-author">${c.author}</span>
        <span class="comment-time">${UI.timeAgo(c.time)}</span>
        ${c.isAI ? '<span class="badge" style="background:var(--accent-dim);color:var(--accent);font-size:10px">AI</span>' : ''}
      </div>
      <div class="${c.isAI ? 'comment-ai' : 'comment-text'}">${c.text}</div>
    </div>
  </div>`).join('');
}

/* ── Tab switching ── */
window.switchCommentTab = function(tab) {
  ['internal','external'].forEach(t => {
    const panel = document.getElementById(`comments-panel-${t}`);
    const btn   = document.getElementById(`tab-${t}`);
    if (!panel || !btn) return;
    const active = t === tab;
    panel.style.display = active ? 'block' : 'none';
    btn.style.color = active ? 'var(--accent)' : 'var(--text3)';
    btn.style.borderBottom = active ? '2px solid var(--accent)' : '2px solid transparent';
  });
};

/* ── Post comment in a tab ── */
async function postTabComment(tab) {
  const textarea = document.getElementById(`reply-${tab}`);
  const text = textarea?.value.trim();
  if (!text) return;
  const author = tab === 'internal' ? 'Sarah Ali' : 'Sarah Ali (Support)';
  await API.addComment(_currentTicketId, { author, text });
  textarea.value = '';
  const ticket = await API.getTicket(_currentTicketId);
  const list = ticket.comments.filter(c => tab === 'internal' ? !isExternal(c) : isExternal(c));
  UI.setHTML(`comments-${tab}`, renderCommentList(list, tab === 'internal' ? 'No internal notes yet.' : 'No customer messages yet.'));
  UI.toast('Comment added', 'success');
}
window.postTabComment = postTabComment;

/* ── AI Draft for a tab ── */
async function generateDraft(tab) {
  const draftEl = document.getElementById(`ai-draft-${tab}`);
  if (!draftEl) return;
  draftEl.style.display = 'block';
  draftEl.textContent = 'Generating…';

  try {
    const ticket = await API.getTicket(_currentTicketId);
    let result;
    if (tab === 'external') {
      result = await AI_API.suggestReply(ticket);
    } else {
      result = await AI_API.callAI(
        `Write a concise internal engineering note for this ticket (2-3 sentences). Cover: current status, suspected root cause, recommended next action.\n\nTicket: ${ticket.title}\nDescription: ${ticket.description}\nPriority: ${ticket.priority}\nTags: ${ticket.tags.join(', ')}\n\nInternal note only. No greeting.`
      );
    }
    draftEl.textContent = result;
    // Pre-fill the textarea
    const textarea = document.getElementById(`reply-${tab}`);
    if (textarea) textarea.value = result;
  } catch (e) {
    draftEl.textContent = 'AI unavailable.';
  }
}
window.generateDraft = generateDraft;

/* ── AI Analysis ── */
async function triggerAIAnalysis(ticketOverride) {
  const ticket = ticketOverride || await API.getTicket(_currentTicketId);
  if (!ticket) return;
  UI.setLoading('ai-detail-response', 'Analyzing…');
  try {
    const result = await AI_API.analyzeTicket(ticket);
    UI.setText('ai-detail-response', result, { italic: false, color: 'var(--text2)' });
  } catch (e) {
    UI.setText('ai-detail-response', 'AI analysis unavailable.', { italic: true });
  }
}

async function draftReply() {
  const ticket = await API.getTicket(_currentTicketId);
  if (!ticket) return;
  UI.setLoading('ai-detail-response', 'Drafting reply…');
  try {
    const result = await AI_API.suggestReply(ticket);
    const el = document.getElementById('ai-detail-response');
    if (el) { el.style.fontStyle='italic'; el.style.color='var(--text)'; el.textContent=result; }
  } catch (e) {
    UI.setText('ai-detail-response', 'AI unavailable.', { italic: true });
  }
}

/* ── AI Chat ── */
async function sendDetailChat() {
  const input = document.getElementById('detail-chat-input');
  const text = input?.value.trim();
  if (!text) return;
  input.value = '';
  const messages = document.getElementById('detail-chat-messages');
  const ticket = await API.getTicket(_currentTicketId);
  messages.innerHTML += `<div class="ai-msg user"><div class="ai-msg-avatar" style="background:var(--surface3);color:var(--text2)">You</div><div class="ai-msg-bubble">${text}</div></div>`;
  const typingId = `typing-${Date.now()}`;
  messages.innerHTML += `<div id="${typingId}" class="ai-msg bot"><div class="ai-msg-avatar" style="background:linear-gradient(135deg,#4f7fff,#a78bfa)">✦</div><div class="ai-msg-bubble"><div class="ai-loading"><div class="ai-dot"></div><div class="ai-dot"></div><div class="ai-dot"></div></div></div></div>`;
  messages.scrollTop = messages.scrollHeight;
  _chatHistory.push({ role:'user', content:text });
  try {
    const context = { ticket, allTickets: window.tickets.filter(t => t.tags.some(tag => ticket.tags.includes(tag)) || t.customerId === ticket.customerId) };
    const reply = await AI_API.chatWithContext(_chatHistory, context);
    _chatHistory.push({ role:'assistant', content:reply });
    document.getElementById(typingId)?.remove();
    messages.innerHTML += `<div class="ai-msg bot"><div class="ai-msg-avatar" style="background:linear-gradient(135deg,#4f7fff,#a78bfa)">✦</div><div class="ai-msg-bubble">${reply}</div></div>`;
    messages.scrollTop = messages.scrollHeight;
  } catch (e) {
    document.getElementById(typingId)?.remove();
    messages.innerHTML += `<div class="ai-msg bot"><div class="ai-msg-avatar" style="background:var(--surface3)">✦</div><div class="ai-msg-bubble" style="color:var(--text3)">AI unavailable.</div></div>`;
  }
}
window.sendDetailChat = sendDetailChat;

/* ── Edit Modal ── */
window.openEditModal = async function () {
  const ticket = await API.getTicket(_currentTicketId);
  if (!ticket) return;
  const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
  setVal('edit-status',    ticket.status);
  setVal('edit-priority',  ticket.priority);
  setVal('edit-assignee',  ticket.assignee);
  setVal('edit-category',  ticket.category);
  setVal('edit-due-date',  ticket.due_date ? ticket.due_date.substring(0,10) : '');
  setVal('edit-ticket-id', ticket.id);
  window._editTags = [...ticket.tags];
  renderEditTags();
  UI.openModal('edit-modal');
};

window.renderEditTags = function () {
  const wrap = document.getElementById('edit-tags-wrap');
  if (!wrap) return;
  const existingInput = wrap.querySelector('input');
  wrap.innerHTML = '';
  window._editTags.forEach((tag, i) => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.innerHTML = `${tag} <button class="tag-remove" onclick="window._editTags.splice(${i},1);window.renderEditTags()">×</button>`;
    wrap.appendChild(chip);
  });
  const inp = document.createElement('input');
  inp.placeholder = 'Add tag…';
  inp.onkeydown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const v = inp.value.trim().replace(',','');
      if (v && !window._editTags.includes(v)) { window._editTags.push(v); window.renderEditTags(); }
    }
  };
  if (existingInput) inp.focus();
  wrap.appendChild(inp);
};

window.saveEdit = async function () {
  const id = document.getElementById('edit-ticket-id')?.value;
  if (!id) return;
  const getVal = (elId) => document.getElementById(elId)?.value;
  const dueDateVal = getVal('edit-due-date');
  const changes = {
    status:   getVal('edit-status'),
    priority: getVal('edit-priority'),
    assignee: getVal('edit-assignee'),
    category: getVal('edit-category'),
    due_date: dueDateVal ? new Date(dueDateVal).toISOString() : null,
    tags:     window._editTags || [],
  };
  try {
    await API.updateTicket(id, changes);
    UI.closeModal('edit-modal');
    UI.toast('Ticket updated', 'success');
    UI.updateStats();
    const updated = await API.getTicket(id);
    renderDetailPage(updated);
    triggerAIAnalysis(updated);
  } catch (e) {
    UI.toast('Failed to update: ' + e.message, 'error');
  }
};
