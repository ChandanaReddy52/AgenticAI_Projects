/* ═══════════════════════════════════════════════
   pages/activity.js — Activity Feed Page
   ═══════════════════════════════════════════════ */

'use strict';

window.Pages = window.Pages || {};

window.Pages.activity = function () {
  const el = document.getElementById('activity-list');
  if (!el) return;

  const log = window.activityLog || [];

  if (!log.length) {
    el.innerHTML = '<div class="empty-state"><p>No activity yet.</p></div>';
    return;
  }

  const typeStyles = {
    created: { bg: 'var(--accent-dim)', icon: '✦' },
    updated: { bg: 'var(--amber-dim)',  icon: '↻' },
    comment: { bg: 'var(--green-dim)',  icon: '💬' },
  };

  el.innerHTML = log.slice(0, 40).map(a => {
    const style = typeStyles[a.type] || typeStyles.updated;
    return `
    <div class="activity-item">
      <div class="activity-icon" style="background:${style.bg}; font-size:12px">${style.icon}</div>
      <div>
        <div class="activity-text">${a.text}</div>
        <div class="activity-time">${UI.timeAgo(a.time)}</div>
      </div>
    </div>`;
  }).join('');
};
