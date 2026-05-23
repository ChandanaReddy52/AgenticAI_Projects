/* ═══════════════════════════════════════════════
   api.js — Simulated REST API Layer

   All data access goes through this module.
   Mirrors real REST endpoints so swapping to a
   live backend requires changing ONLY this file.

   Endpoints simulated:
     GET    /tickets
     GET    /tickets/:id
     POST   /tickets
     PUT    /tickets/:id
     DELETE /tickets/:id
     GET    /customers
     GET    /customers/:id
     POST   /tickets/:id/comments
   ═══════════════════════════════════════════════ */

'use strict';

/* Simulate async network latency */
const delay = (ms = 60) => new Promise(r => setTimeout(r, ms));

/* ── Tickets ── */

window.API = {

  async getTickets({ status, priority, category, source, search } = {}) {
    await delay();
    let results = [...window.tickets];

    if (status)   results = results.filter(t => t.status   === status);
    if (priority) results = results.filter(t => t.priority === priority);
    if (category) results = results.filter(t => t.category === category);
    if (source)   results = results.filter(t => t.source   === source);
    if (search) {
      const q = search.toLowerCase();
      results = results.filter(t =>
        t.title.toLowerCase().includes(q)       ||
        t.description.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q)          ||
        t.tags.some(tag => tag.includes(q))
      );
    }

    return results.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  },

  async getTicket(id) {
    await delay();
    return window.tickets.find(t => t.id === id) || null;
  },

  async createTicket(data) {
    await delay(100);
    const id = `TKT-${window.ticketCounter++}`;
    const now = new Date().toISOString();

    const ticket = {
      id,
      title:       data.title,
      description: data.description,
      priority:    data.priority    || 'medium',
      status:      'open',
      category:    data.category    || 'Query',
      source:      data.source      || 'Manual',
      tags:        data.tags        || [],
      assignee:    data.assignee    || 'Unassigned',
      customerId:  data.customerId  || null,
      created_at:  now,
      updated_at:  now,
      due_date:    data.due_date    || null,
      timeline: [{ action: 'Ticket created', time: now, author: data.assignee || 'Agent' }],
      comments: [],
    };

    window.tickets.unshift(ticket);
    window.activityLog.unshift({
      type: 'created', ticketId: id,
      text: `Ticket <strong>${id}</strong> created — ${data.title.substring(0,60)}`,
      time: now,
    });

    return ticket;
  },

  async updateTicket(id, changes) {
    await delay(80);
    const idx = window.tickets.findIndex(t => t.id === id);
    if (idx === -1) throw new Error('Ticket not found');

    const old = window.tickets[idx];
    const now = new Date().toISOString();

    // Log meaningful changes to timeline
    const changeLines = [];
    if (changes.status   && changes.status   !== old.status)   changeLines.push(`Status: ${old.status} → ${changes.status}`);
    if (changes.priority && changes.priority !== old.priority) changeLines.push(`Priority: ${old.priority} → ${changes.priority}`);
    if (changes.assignee && changes.assignee !== old.assignee) changeLines.push(`Assigned to: ${changes.assignee}`);
    if (changes.category && changes.category !== old.category) changeLines.push(`Category: ${old.category} → ${changes.category}`);

    const updated = {
      ...old,
      ...changes,
      updated_at: now,
      timeline: [
        ...old.timeline,
        ...changeLines.map(action => ({ action, time: now, author: 'Agent' })),
      ],
    };

    window.tickets[idx] = updated;

    if (changeLines.length) {
      window.activityLog.unshift({
        type: 'updated', ticketId: id,
        text: `<strong>${id}</strong> updated — ${changeLines.join(', ')}`,
        time: now,
      });
    }

    return updated;
  },

  async addComment(ticketId, { author, text, isAI = false }) {
    await delay(50);
    const ticket = window.tickets.find(t => t.id === ticketId);
    if (!ticket) throw new Error('Ticket not found');

    const comment = {
      id: `c${Date.now()}`,
      author, text, isAI,
      time: new Date().toISOString(),
    };

    ticket.comments.push(comment);
    ticket.updated_at = comment.time;

    window.activityLog.unshift({
      type: 'comment', ticketId,
      text: `<strong>${author}</strong> commented on <strong>${ticketId}</strong>`,
      time: comment.time,
    });

    return comment;
  },

  /* ── Customers ── */

  async getCustomers() {
    await delay();
    return [...window.customers];
  },

  async getCustomer(id) {
    await delay();
    return window.customers.find(c => c.id === id) || null;
  },

  async getCustomerTickets(customerId) {
    await delay();
    return window.tickets.filter(t => t.customerId === customerId)
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  },
};
