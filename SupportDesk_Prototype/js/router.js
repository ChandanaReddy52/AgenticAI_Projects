/* ═══════════════════════════════════════════════
   router.js — Client-Side SPA Router

   Manages page transitions without full reloads.
   Uses URL hash (#page/param) for deep-linking.

   Design Decision:
     Hash-based routing (no server config needed).
     Each route maps to a render function in
     the corresponding page JS module.
     History pushState updates the URL so users
     can copy/share deep links to specific tickets.
   ═══════════════════════════════════════════════ */

'use strict';

/* ── Route Registry ──
   Maps route names to { title, renderFn, navId }
   renderFn receives (params) from the URL         */
const ROUTES = {
  'dashboard':  { title: 'Dashboard',          nav: 'nav-dashboard',  render: () => window.Pages.dashboard() },
  'tickets':    { title: 'All Tickets',         nav: 'nav-tickets',    render: () => window.Pages.tickets() },
  'new-ticket': { title: 'New Ticket',          nav: 'nav-new-ticket', render: () => window.Pages.newTicket() },
  'detail':     { title: 'Ticket Detail',       nav: null,             render: (p) => window.Pages.detail(p) },
  'customers':  { title: 'Customers',           nav: 'nav-customers',  render: () => window.Pages.customers() },
  'customer':   { title: 'Customer Detail',     nav: null,             render: (p) => window.Pages.customerDetail(p) },
  'insights':   { title: 'AI Insights Hub',     nav: 'nav-insights',   render: () => window.Pages.insights() },
  'activity':   { title: 'Activity Feed',       nav: 'nav-activity',   render: () => window.Pages.activity() },
};

window.Router = {

  current: null,
  currentParam: null,

  /* Navigate to a route programmatically */
  go(route, param = null) {
    const hash = param ? `#${route}/${param}` : `#${route}`;
    window.history.pushState({ route, param }, '', hash);
    this._render(route, param);
  },

  /* Parse and render from current URL hash */
  resolve() {
    const hash   = window.location.hash.replace('#', '') || 'dashboard';
    const parts  = hash.split('/');
    const route  = parts[0];
    const param  = parts[1] || null;
    this._render(route, param);
  },

  /* Internal render */
  _render(route, param) {
    const def = ROUTES[route] || ROUTES['dashboard'];

    /* Hide all pages */
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

    /* Show target page */
    const pageEl = document.getElementById(`page-${route}`);
    if (pageEl) pageEl.classList.add('active');

    /* Update page title */
    const titleEl = document.getElementById('page-title');
    if (titleEl) {
      titleEl.textContent = route === 'detail' && param ? `Ticket ${param}` : def.title;
    }

    /* Update nav active state */
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    if (def.nav) {
      const navEl = document.getElementById(def.nav);
      if (navEl) navEl.classList.add('active');
    }

    this.current      = route;
    this.currentParam = param;

    /* Call the page render function */
    if (def.render) def.render(param);

    /* Always update stats */
    UI.updateStats();

    /* Scroll to top */
    document.querySelector('.main')?.scrollTo(0, 0);
  },
};

/* Handle browser back/forward */
window.addEventListener('popstate', () => Router.resolve());
