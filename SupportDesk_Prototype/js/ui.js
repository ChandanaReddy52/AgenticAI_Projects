/* ═══════════════════════════════════════════════
   ui.js — Shared UI Helpers

   Render utilities used across all pages:
   - Badge generators
   - Toast notifications
   - Time formatting + SLA status
   - Stats updater
   - Modal helpers
   ═══════════════════════════════════════════════ */

'use strict';

/* ──────────────────────────────────────────────
   BADGES
   ────────────────────────────────────────────── */

window.UI = {

  statusBadge(s) {
    const map = {
      'open':        ['badge-open',        'Open'],
      'in-progress': ['badge-in-progress', 'In Progress'],
      'resolved':    ['badge-resolved',    'Resolved'],
      'closed':      ['badge-closed',      'Closed'],
    };
    const [cls, label] = map[s] || ['badge-open', s];
    return `<span class="badge ${cls}"><span class="badge-dot"></span>${label}</span>`;
  },

  priorityBadge(p) {
    const map = {
      'critical': 'badge-critical',
      'high':     'badge-high',
      'medium':   'badge-medium',
      'low':      'badge-low',
    };
    const icons = { critical: '🔴', high: '🟠', medium: '🔵', low: '🟢' };
    return `<span class="badge ${map[p] || 'badge-medium'}" style="text-transform:capitalize">${p}</span>`;
  },

  categoryBadge(c) {
    const map = {
      'Bug':             'badge-bug',
      'Feature Request': 'badge-feature',
      'Feature Upgrade': 'badge-upgrade',
      'Incident':        'badge-incident',
      'Query':           'badge-query',
    };
    return `<span class="badge ${map[c] || 'badge-query'}">${c}</span>`;
  },

  sourceBadge(s) {
    const map = {
      'Email':  'badge-email',
      'Chat':   'badge-chat',
      'API':    'badge-api',
      'Manual': 'badge-manual',
    };
    const icons = { Email: '✉', Chat: '💬', API: '⚡', Manual: '✏' };
    return `<span class="badge ${map[s] || 'badge-manual'}">${icons[s] || ''} ${s}</span>`;
  },

  tagChips(tags = []) {
    if (!tags.length) return '<span style="color:var(--text4);font-size:12px">—</span>';
    return tags.map(t => `<span class="tag-chip">${t}</span>`).join('');
  },

  /* ──────────────────────────────────────────────
     TIME & SLA
     ────────────────────────────────────────────── */

  timeAgo(iso) {
    const diff = (Date.now() - new Date(iso)) / 1000;
    if (diff < 60)    return 'just now';
    if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  },

  formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  },

  slaStatus(dueDateIso) {
    if (!dueDateIso) return { label: 'No SLA', cls: 'mono-label', urgency: 'none' };
    const msLeft = new Date(dueDateIso) - Date.now();
    const hLeft  = msLeft / 3600000;

    if (msLeft < 0)    return { label: 'SLA Breached',     cls: 'sla-breached', urgency: 'breached' };
    if (hLeft < 4)     return { label: `${Math.ceil(hLeft)}h left`,  cls: 'sla-warning', urgency: 'critical' };
    if (hLeft < 24)    return { label: `${Math.ceil(hLeft)}h left`,  cls: 'sla-warning', urgency: 'warning' };
    const dLeft = Math.ceil(hLeft / 24);
    return { label: `${dLeft}d left`, cls: 'sla-ok', urgency: 'ok' };
  },

  /* ──────────────────────────────────────────────
     TOAST NOTIFICATIONS
     ────────────────────────────────────────────── */

  toast(msg, type = 'success') {
    const wrap = document.getElementById('toasts');
    const el   = document.createElement('div');
    el.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
    el.innerHTML = `<span style="font-weight:600">${icon}</span> ${msg}`;
    wrap.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity 0.3s'; setTimeout(() => el.remove(), 300); }, 3000);
  },

  /* ──────────────────────────────────────────────
     MODAL HELPERS
     ────────────────────────────────────────────── */

  openModal(id)  { document.getElementById(id)?.classList.add('open'); },
  closeModal(id) { document.getElementById(id)?.classList.remove('open'); },

  /* ──────────────────────────────────────────────
     STATS BAR
     ────────────────────────────────────────────── */

  updateStats() {
    const t = window.tickets;
    const total    = t.length;
    const open     = t.filter(x => x.status === 'open').length;
    const inprog   = t.filter(x => x.status === 'in-progress').length;
    const resolved = t.filter(x => x.status === 'resolved').length;
    const critical = t.filter(x => x.priority === 'critical').length;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    set('stat-total',    total);
    set('stat-open',     open);
    set('stat-ip',       inprog);
    set('stat-resolved', resolved);
    set('stat-critical', critical);

    // Nav badges
    set('nav-count',      total);
    set('nav-open',       open);
    set('nav-inprogress', inprog);
    set('nav-resolved',   resolved);

    // SLA breached count
    const breached = t.filter(x => {
      if (!x.due_date || x.status === 'resolved' || x.status === 'closed') return false;
      return new Date(x.due_date) < Date.now();
    }).length;
    set('stat-sla', breached);
    set('nav-sla',  breached);
  },

  /* ──────────────────────────────────────────────
     CUSTOMER HEALTH
     ────────────────────────────────────────────── */

  healthColor(score) {
    if (score >= 70) return 'health-good';
    if (score >= 45) return 'health-warning';
    return 'health-danger';
  },

  healthLabel(score) {
    if (score >= 70) return { label: 'Healthy',    color: 'var(--green)' };
    if (score >= 45) return { label: 'At Risk',    color: 'var(--amber)' };
    return               { label: 'Critical',  color: 'var(--red)' };
  },

  formatARR(n) {
    if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
    return `$${Math.round(n / 1000)}K`;
  },

  /* ──────────────────────────────────────────────
     LOADING STATE
     ────────────────────────────────────────────── */

  setLoading(elId, text = 'Loading...') {
    const el = document.getElementById(elId);
    if (!el) return;
    el.innerHTML = `<div class="ai-loading"><div class="ai-dot"></div><div class="ai-dot"></div><div class="ai-dot"></div><span style="font-size:12px;color:var(--text3);margin-left:6px">${text}</span></div>`;
  },

  setText(elId, text, opts = {}) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    if (opts.color) el.style.color = opts.color;
    if (opts.italic !== undefined) el.style.fontStyle = opts.italic ? 'italic' : 'normal';
  },

  setHTML(elId, html) {
    const el = document.getElementById(elId);
    if (el) el.innerHTML = html;
  },
};
