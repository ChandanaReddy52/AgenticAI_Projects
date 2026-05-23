/* data.js - GlobalFoods SupportDesk - 24 tickets with sentiment_score per ticket */
'use strict';

function daysAgo(n) { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString(); }
function hoursAgo(n) { return new Date(Date.now() - n * 3600000).toISOString(); }
function daysFromNow(n) { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString(); }

window.customers = [
  { id:'CUST-001', name:'GlobalFoods HQ',        industry:'Food Distribution', arr:1200000, plan:'Enterprise', health:40, csm:'Sarah Ali',  since:'2022-04-10', contact:'Marcus Webb', email:'marcus.webb@globalfoods.com' },
  { id:'CUST-002', name:'FreshMart Retail Group', industry:'Retail Chain',      arr:1500000, plan:'Enterprise', health:35, csm:'James Park', since:'2021-09-01', contact:'Priya Nair',  email:'priya.nair@freshmart.com' },
  { id:'CUST-003', name:'Logix Pharma Supply',    industry:'Pharma Logistics',  arr:700000,  plan:'Enterprise', health:55, csm:'Riya Patel', since:'2023-01-15', contact:'Dr. Okafor',  email:'okafor@logixpharma.com' },
  { id:'CUST-004', name:'QuickShip Warehousing',  industry:'3PL Logistics',     arr:500000,  plan:'Business',   health:72, csm:'Dev Kumar',  since:'2023-06-20', contact:'Laura Chen',  email:'laura.chen@quickship.com' },
  { id:'CUST-005', name:'AgriSource Suppliers',   industry:'Supplier Network',  arr:900000,  plan:'Enterprise', health:68, csm:'Sarah Ali',  since:'2022-11-03', contact:'Ravi Menon',  email:'ravi.menon@agrisource.com' },
];

/* sentiment_score: 1-3=Positive 4-6=Neutral 7-9=Negative
   Week(8):    3 Negative(7-9) + 4 Neutral(4-6) + 1 Positive(1-3)
   Month(8):   2 Negative      + 2 Neutral       + 4 Positive(1-3)
   Quarter(8): 1 Negative      + 2 Neutral        + 5 Positive(1-3)  */
window.tickets = [

  /* === WEEK === */
  {
    id:'TKT-1001', sentiment_score:8,
    title:'App crash on network reconnect silently corrupts pending order queue',
    description:'Field reps offline 2+ hours see a silent crash when the app reconnects. Pending orders queue corrupted and lost. No error surfaced — reps believe orders were submitted. Root strongly suspected: NetworkManager fires before DNS resolves, triggering a sync attempt that crashes mid-write. On restart, retry sends a second POST without idempotency key.',
    priority:'high', status:'open', category:'Incident', source:'Email',
    tags:['sync','crash','offline','data-loss','idempotency-missing'],
    assignee:'Dev Kumar', customerId:'CUST-001',
    created_at:hoursAgo(36), updated_at:hoursAgo(4), due_date:daysFromNow(1),
    timeline:[
      { action:'Ticket created via VP escalation email', time:hoursAgo(36), author:'Sarah Ali' },
      { action:'Priority escalated to High', time:hoursAgo(20), author:'Dev Kumar' },
      { action:'Linked to TKT-1002 — same root cause suspected', time:hoursAgo(4), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c1a', author:'Dev Kumar', text:'Root cause strongly suspected — validation ongoing. POST /api/orders sent mid-crash with no idempotency key. On restart, sync retries the same POST — server creates a duplicate order. Fix: add Idempotency-Key header to all order POSTs.', time:hoursAgo(18), isAI:false },
      { id:'c1b', author:'Marcus Webb (GlobalFoods VP Ops)', text:'Our reps are losing 5-8 orders per week. Critical dispatch miss this morning. If unresolved within 7 days, we are pausing the platform rollout to our western region distribution network. I am copying our legal team.', time:hoursAgo(6), isAI:false },
      { id:'c1c', author:'Sarah Ali', text:'Temporary workaround issued: field teams advised to avoid offline order submissions and place orders only when connected. Reduces duplicate-submit risk but directly impacts rep productivity — rural zones reporting 30-40% slower order processing. Stopgap only.', time:hoursAgo(3), isAI:false },
    ],
  },
  {
    id:'TKT-1002', sentiment_score:9,
    title:'Duplicate purchase orders after reconnect — POST /api/orders missing Idempotency-Key header',
    description:'Sync queue retries order POST without any idempotency key. Server creates a second purchase order every time. Caused $42K billing discrepancies at FreshMart across 12 store locations. Affects any order created offline and synced after a connectivity interruption.',
    priority:'critical', status:'in-progress', category:'Incident', source:'API',
    tags:['sync','duplicate','offline','idempotency-missing','billing','finance'],
    assignee:'Dev Kumar', customerId:'CUST-002',
    created_at:hoursAgo(42), updated_at:hoursAgo(2), due_date:daysFromNow(0),
    timeline:[
      { action:'Auto-created via API monitoring — duplicate order rate exceeded threshold', time:hoursAgo(42), author:'System' },
      { action:'Linked to FreshMart escalation', time:hoursAgo(38), author:'James Park' },
      { action:'Status: open → in-progress', time:hoursAgo(20), author:'Dev Kumar' },
      { action:'Root cause strongly suspected: POST /api/orders missing Idempotency-Key', time:hoursAgo(8), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c2a', author:'Dev Kumar', text:'Root cause strongly suspected — validation ongoing. POST /api/orders has no idempotency key support. Every retry creates a new order on the server. Fix: (1) Add Idempotency-Key header. (2) Store keys in Redis 72h TTL. (3) Return 200 with original order ID on duplicate key. Backend PR open.', time:hoursAgo(14), isAI:false },
      { id:'c2b', author:'James Park', text:'FreshMart CFO escalated. $42K billing discrepancy blocking monthly financial close. Priya Nair: "Contract renewal in August depends entirely on this being fixed."', time:hoursAgo(8), isAI:false },
      { id:'c2c', author:'System Monitor', text:'AUTOMATED ALERT: Duplicate order rate 3.2x baseline over last 24 hours. 47 confirmed duplicate order pairs across CUST-001, CUST-002, CUST-005. Estimated financial exposure: $67K.', time:hoursAgo(2), isAI:false },
      { id:'c2d', author:'Platform Analytics', text:'TREND SIGNAL: Duplicate order incidents increased 2.8x over past 14 days (week 1: 17 incidents, week 2: 47 incidents). Sync failure rate risen from 6.1% to 18.4%. Retry loop triggered in 34% of offline sessions vs 11% baseline 30 days ago. Rate of change is accelerating.', time:hoursAgo(1), isAI:false },
    ],
  },
  {
    id:'TKT-1003', sentiment_score:7,
    title:'Orders silently missing from warehouse queue after partial sync failure',
    description:'Field rep orders created offline not appearing in WMS after sync. Sync logs show partial write errors — some orders reach API but WMS integration callback fails silently. 31 missing orders discovered when a distributor called to chase deliveries.',
    priority:'high', status:'open', category:'Incident', source:'Email',
    tags:['sync','offline','duplicate','missing-orders','warehouse','dispatch'],
    assignee:'Riya Patel', customerId:'CUST-001',
    created_at:hoursAgo(28), updated_at:hoursAgo(6), due_date:daysFromNow(0),
    timeline:[
      { action:'Raised by GlobalFoods warehouse ops manager', time:hoursAgo(28), author:'Sarah Ali' },
      { action:'31 missing orders confirmed across 4 distribution centres', time:hoursAgo(22), author:'Riya Patel' },
      { action:'Linked to TKT-1001, TKT-1002 — same idempotency root', time:hoursAgo(10), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c3a', author:'Riya Patel', text:'Sync retry loop sending duplicate POST requests to WMS callback endpoint too — idempotency missing at integration layer, not just order creation. Need idempotency keys end-to-end.', time:hoursAgo(12), isAI:false },
      { id:'c3b', author:'Marcus Webb (GlobalFoods VP Ops)', text:'Supply chain integrity failure. 31 orders undeliverable. If unresolved in 7 days, rollout paused to 4 additional regions. Copying legal team.', time:hoursAgo(4), isAI:false },
    ],
  },
  {
    id:'TKT-1004', sentiment_score:5,
    title:'FreshMart retail buyer charged twice — $42K duplicate billing across 12 store locations',
    description:'FreshMart finance identified billing discrepancies across 12 stores. Same purchase order invoiced twice. Duplicates created by sync retry mechanism — offline order submitted twice when app reconnected after intermittent WiFi. Financial reconciliation blocked before month-end close.',
    priority:'high', status:'open', category:'Incident', source:'Email',
    tags:['sync','duplicate','offline','billing','finance','idempotency-missing'],
    assignee:'James Park', customerId:'CUST-002',
    created_at:hoursAgo(20), updated_at:hoursAgo(3), due_date:daysFromNow(1),
    timeline:[
      { action:'Raised by FreshMart CFO office', time:hoursAgo(20), author:'James Park' },
      { action:'Confirmed: same root cause as TKT-1002', time:hoursAgo(10), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c4a', author:'James Park', text:'12-store impact because stores use mobile app offline with spotty WiFi. Each reconnect triggers retry-loop submitting same order multiple times via duplicate POST requests. Financial reconciliation blocked until duplicates are credited.', time:hoursAgo(14), isAI:false },
      { id:'c4b', author:'Priya Nair (FreshMart COO)', text:'Our CFO flagged this as P0. Financial reconciliation before month-end is blocked. $1.5M renewal is at risk. If billing not resolved before August 15 contract renewal, we will be evaluating alternative vendors.', time:hoursAgo(3), isAI:false },
    ],
  },
  {
    id:'TKT-1016', sentiment_score:4,
    title:'Order shown as Confirmed before sync completes — trust breakdown when sync fails',
    description:'Mobile app applies optimistic UI update marking orders "Confirmed" on tap, before backend sync completes. When sync fails, buyer sees a confirmed order that does not exist in the backend. UI lies about order state.',
    priority:'high', status:'open', category:'Bug', source:'Email',
    tags:['sync','offline','ux','trust','status'],
    assignee:'Sarah Ali', customerId:'CUST-002',
    created_at:hoursAgo(30), updated_at:hoursAgo(8), due_date:daysFromNow(1),
    timeline:[
      { action:'Raised by FreshMart regional manager', time:hoursAgo(30), author:'James Park' },
      { action:'Confirmed: optimistic UI not rolled back on sync failure', time:hoursAgo(16), author:'Sarah Ali' },
    ],
    comments:[
      { id:'c16a', author:'Sarah Ali', text:'Fix: only show Confirmed after receiving 200 from POST /api/orders with server-assigned order ID. Optimistic Confirmed state must be replaced with Pending Sync state until idempotent POST succeeds.', time:hoursAgo(8), isAI:false },
    ],
  },
  {
    id:'TKT-1018', sentiment_score:6,
    title:'Audit logs missing for failed offline transactions — GxP and SOX compliance gap at Logix Pharma',
    description:'Logix Pharma requires complete audit trail for all order creation attempts. When offline order fails sync and is dropped, no log record created. Material finding ahead of Q3 regulatory audit in 14 days.',
    priority:'high', status:'open', category:'Incident', source:'Email',
    tags:['sync','offline','audit','compliance','sox','regulatory'],
    assignee:'Sarah Ali', customerId:'CUST-003',
    created_at:hoursAgo(40), updated_at:hoursAgo(10), due_date:daysFromNow(12),
    timeline:[
      { action:'Escalated by Logix Pharma compliance director Dr. Okafor', time:hoursAgo(40), author:'Sarah Ali' },
      { action:'Regulatory audit confirmed: 14 days from today', time:hoursAgo(20), author:'Sarah Ali' },
      { action:'Hard deadline: audit log data required within 12 days', time:hoursAgo(8), author:'Riya Patel' },
    ],
    comments:[
      { id:'c18a', author:'Dr. Okafor (Logix Pharma Compliance)', text:'Q3 regulatory audit begins in 14 days and cannot be rescheduled. If audit-ready data not available within 12 business days, we must file a material gap report. $700K renewal and our regulatory standing depend on resolution before audit date.', time:hoursAgo(10), isAI:false },
    ],
  },
  {
    id:'TKT-1020', sentiment_score:8,
    title:'GlobalFoods VP formal notice — platform rollout paused citing systemic data reliability failures',
    description:'GlobalFoods VP of Operations Marcus Webb sent formal written notice to VP Customer Success. Pausing platform rollout to 4 additional distribution regions citing 6 open tickets, 31 missing orders, and 18 permanently lost orders in 7 days. Expansion represents $800K incremental ARR.',
    priority:'critical', status:'open', category:'Incident', source:'Email',
    tags:['sync','offline','escalation','churn-risk','contract','vp-escalation'],
    assignee:'Sarah Ali', customerId:'CUST-001',
    created_at:hoursAgo(18), updated_at:hoursAgo(2), due_date:daysFromNow(7),
    timeline:[
      { action:'Formal notice received — escalated to VP Customer Success', time:hoursAgo(18), author:'Sarah Ali' },
      { action:'Emergency internal review scheduled', time:hoursAgo(6), author:'Sarah Ali' },
      { action:'7-day response deadline confirmed — RCA required by end of business Friday', time:hoursAgo(2), author:'Sarah Ali' },
    ],
    comments:[
      { id:'c20a', author:'Sarah Ali', text:'GlobalFoods largest expansion opportunity — 4 regions = $800K incremental ARR. All 6 cited tickets share same root cause: missing idempotency in sync APIs. If we ship idempotency fix this sprint, we can respond to Marcus with credible resolution timeline.', time:hoursAgo(12), isAI:false },
      { id:'c20b', author:'Marcus Webb (GlobalFoods VP Ops)', text:'Setting a 7-day clock from this notice. By end of business Friday I require: (1) written root cause analysis, (2) specific fix deployment date, and (3) rollback plan. If we do not receive all three, board review Monday will include recommendation to evaluate alternative platforms.', time:hoursAgo(2), isAI:false },
    ],
  },
  {
    id:'TKT-1021', sentiment_score:4,
    title:'FreshMart formal SLA credit claim $18K — August renewal explicitly at risk',
    description:'FreshMart legal submitted formal SLA credit claim for 23 delivery SLA breaches at $800 per incident. August 15 renewal discussion explicitly linked by COO to resolution of sync reliability. Live demo of fixed system required before August 15.',
    priority:'high', status:'open', category:'Incident', source:'Email',
    tags:['sync','offline','sla-credit','legal','contract','churn-risk','escalation'],
    assignee:'James Park', customerId:'CUST-002',
    created_at:hoursAgo(22), updated_at:hoursAgo(5), due_date:daysFromNow(7),
    timeline:[
      { action:'SLA credit claim received from FreshMart legal', time:hoursAgo(22), author:'James Park' },
      { action:'Escalated to VP Sales and VP Customer Success', time:hoursAgo(18), author:'James Park' },
    ],
    comments:[
      { id:'c21a', author:'James Park', text:'$1.5M ARR at risk. COO made it explicit: fix sync reliability and billing duplicates by August 1 or renewal discussion will not proceed. That is 6 weeks. Idempotency fix must ship in the next 2 sprints.', time:hoursAgo(14), isAI:false },
      { id:'c21b', author:'Priya Nair (FreshMart COO)', text:'Demonstrate working fix to duplicate billing and order confirmation reliability by August 1, and we renew and expand. Miss that date, and we tender the contract. I want a live demo of the fixed system before August 15 — not a slide deck.', time:hoursAgo(5), isAI:false },
    ],
  },

  /* === MONTH === */
  {
    id:'TKT-1005', sentiment_score:7,
    title:'Orders permanently lost when sync retry limit exhausted — no notification, no recovery path',
    description:'After 5 retry attempts, sync client moves orders to "failed" state and removes from retry queue. No notification to field rep. Retry-loop is not idempotent: each of 5 retry attempts sends a duplicate POST /api/orders. Some orders are duplicated (on eventual success), others permanently lost (when retries exhaust).',
    priority:'high', status:'resolved', category:'Incident', source:'API',
    tags:['sync','offline','data-loss','retry-loop','idempotency-missing','notification'],
    assignee:'Dev Kumar', customerId:'CUST-001',
    created_at:daysAgo(12), updated_at:daysAgo(10), due_date:daysAgo(9),
    timeline:[
      { action:'Detected via API monitoring — failed order rate 4x baseline', time:daysAgo(12), author:'System' },
      { action:'Confirmed: retry-loop sends duplicate POSTs then silently drops order', time:daysAgo(11), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c5a', author:'Dev Kumar', text:'Retry-loop amplifies the idempotency problem. Each of 5 automatic retries sends new POST /api/orders with no idempotency key — potentially creating 5 duplicate orders if network recovers mid-retry. When retries exhaust, order dropped with no record. Idempotency fix resolves both failure modes.', time:daysAgo(10), isAI:false },
    ],
  },
  {
    id:'TKT-1007', sentiment_score:4,
    title:'iOS background sync killed by OS — BGProcessingTask 30-second limit drops large order queues',
    description:'Order backlogs of 30+ items cannot complete within iOS BGProcessingTask 30-second window. OS kills sync mid-queue, leaving partial state. Partial state also creates idempotency risk: already-sent orders in partial run are re-sent on next open without idempotency keys, risking duplicates.',
    priority:'high', status:'in-progress', category:'Bug', source:'Manual',
    tags:['sync','offline','ios','background-sync','idempotency-missing'],
    assignee:'Riya Patel', customerId:'CUST-001',
    created_at:daysAgo(28), updated_at:daysAgo(24), due_date:daysAgo(20),
    timeline:[
      { action:'Confirmed: BGProcessingTask limit 30s on iOS 17+', time:daysAgo(28), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c7a', author:'Dev Kumar', text:'Partial sync creates another duplicate-submit risk without idempotency. Orders sent in partial run will be re-sent on next app open. Fix requires: (1) idempotency keys on all POSTs, and (2) chunked sync via batch endpoint.', time:daysAgo(24), isAI:false },
    ],
  },
  {
    id:'TKT-1008', sentiment_score:2,
    title:'Sync queue permanently frozen in "syncing" state when app backgrounded during active sync',
    description:'iOS suspends app mid-sync, cancels in-flight HTTP request. Queue item stuck in "syncing" state permanently — on next open, sync engine skips it. Orders never re-submitted. Fix: on resume, reset "syncing" items to "pending". Also requires idempotency keys so re-submitting in-flight orders does not create duplicates.',
    priority:'high', status:'in-progress', category:'Bug', source:'Chat',
    tags:['sync','offline','ios','data-loss','duplicate-submit'],
    assignee:'Dev Kumar', customerId:'CUST-002',
    created_at:daysAgo(25), updated_at:daysAgo(21), due_date:daysAgo(18),
    timeline:[
      { action:'Linked to TKT-1007 — same iOS lifecycle root', time:daysAgo(22), author:'Dev Kumar' },
    ],
    comments:[],
  },
  {
    id:'TKT-1010', sentiment_score:8,
    title:'Field reps in rural zones reporting 40% sync failure rate — manual retry causing duplicates',
    description:'GlobalFoods reps on rural delivery routes: 4 in 10 submissions fail on first attempt. Reps retry manually 2-3 times per order. Without idempotency keys, each manual retry is a new POST /api/orders. When earlier delayed request eventually lands, server creates both — resulting in duplicate orders.',
    priority:'high', status:'in-progress', category:'Bug', source:'Chat',
    tags:['sync','offline','duplicate','retry-loop','idempotency-missing','network'],
    assignee:'Riya Patel', customerId:'CUST-001',
    created_at:daysAgo(22), updated_at:daysAgo(18), due_date:daysAgo(16),
    timeline:[
      { action:'Pattern confirmed — rural zone connectivity primary trigger', time:daysAgo(20), author:'Riya Patel' },
    ],
    comments:[
      { id:'c10-tension', author:'Ananya Krishnan (Finance Ops, GlobalFoods)', text:'Flagging for awareness — finance team noticed small but unexplained uptick in order count vs shipments dispatched over past 10 days. Not confirmed as systemic yet. Could be a reporting lag. Investigating before raising formally.', time:daysAgo(19), isAI:false },
      { id:'c10a', author:'Riya Patel', text:'Manual retry is a second class of duplicate-submit beyond the automatic retry-loop. Without idempotency keys, both the manual retry and delayed delivery of the first attempt reach the server as separate POSTs. Same root cause as TKT-1002.', time:daysAgo(18), isAI:false },
    ],
  },
  {
    id:'TKT-1011', sentiment_score:5,
    title:'WMS integration timing out on high-volume sync days — warehouse dispatch queue backing up silently',
    description:'QuickShip WMS integration times out when inbound sync volume exceeds 100 orders/hour. Callback failure causes orders to exist in our system but not reach the warehouse. Retrying failed callback creates duplicate dispatch entries in WMS — idempotency missing at integration callback layer too.',
    priority:'high', status:'in-progress', category:'Incident', source:'API',
    tags:['sync','duplicate','warehouse','integration','timeout','idempotency-missing'],
    assignee:'James Park', customerId:'CUST-004',
    created_at:daysAgo(20), updated_at:daysAgo(17), due_date:daysAgo(13),
    timeline:[
      { action:'Reported by QuickShip warehouse supervisor', time:daysAgo(20), author:'James Park' },
    ],
    comments:[
      { id:'c11-misdiag', author:'James Park', text:'Initial assumption was WMS latency spikes were primary cause. QuickShip ops team ran diagnostics and found no WMS-side anomalies. Further analysis suggests upstream duplicate-submit pattern from offline sync may be inflating inbound order volume. Investigating whether WMS overload is a symptom rather than root cause.', time:daysAgo(19), isAI:false },
      { id:'c11a', author:'James Park', text:'WMS callback retry creates duplicate dispatch entries — idempotency missing at integration layer too. Systemic design gap.', time:daysAgo(17), isAI:false },
    ],
  },
  {
    id:'TKT-1013', sentiment_score:1,
    title:'Buyers re-submitting orders with no sync status visible — duplicate POSTs from UX gap',
    description:'Store buyers cannot tell whether an offline order has been synced. No pending or syncing state shown. Buyers tap Submit a second time, assuming first attempt failed. Each re-submission fires a new POST /api/orders without idempotency key, creating duplicate orders.',
    priority:'medium', status:'resolved', category:'Feature Upgrade', source:'Chat',
    tags:['sync','duplicate','offline','ux','visibility','duplicate-submit'],
    assignee:'Sarah Ali', customerId:'CUST-002',
    created_at:daysAgo(15), updated_at:daysAgo(12), due_date:daysAgo(9),
    timeline:[
      { action:'Pattern identified from 5 FreshMart store manager chat sessions', time:daysAgo(15), author:'Sarah Ali' },
    ],
    comments:[
      { id:'c13a', author:'Sarah Ali', text:'Even after backend idempotency fix, we need this UX change. UX fix and idempotency fix must ship together in the same release.', time:daysAgo(12), isAI:false },
    ],
  },
  {
    id:'TKT-1014', sentiment_score:3,
    title:'Inventory misalignment at AgriSource — duplicate orders creating false stock reservation spikes',
    description:'Duplicate orders from re-submission pattern processed by inventory reservation system before duplicates are caught. AgriSource warehouse over-reserving stock. When duplicates are cancelled, stock lock not released promptly. Genuine orders from other distributors cannot be fulfilled.',
    priority:'medium', status:'in-progress', category:'Incident', source:'Email',
    tags:['sync','duplicate','offline','inventory','ops','duplicate-submit'],
    assignee:'Riya Patel', customerId:'CUST-005',
    created_at:daysAgo(18), updated_at:daysAgo(15), due_date:daysAgo(12),
    timeline:[
      { action:'Reported by AgriSource supply chain director Ravi Menon', time:daysAgo(18), author:'Sarah Ali' },
    ],
    comments:[
      { id:'c14a', author:'Riya Patel', text:'Duplicate-submit loop propagating downstream into inventory. Idempotency fix must stop upstream duplicates before we can clean up inventory misalignment downstream.', time:daysAgo(15), isAI:false },
    ],
  },
  {
    id:'TKT-1024', sentiment_score:2,
    title:'FreshMart store manager reports unexplained order count discrepancy — not yet formally investigated',
    description:'A FreshMart store manager at Eastfield location noticed order management portal showing 3 fewer pending orders than team activity log indicated. Raised informally. Initial response suggested display refresh delay. No formal investigation opened. Marked for monitoring.',
    priority:'medium', status:'resolved', category:'Query', source:'Chat',
    tags:['sync','visibility','ux'],
    assignee:'James Park', customerId:'CUST-002',
    created_at:daysAgo(18), updated_at:daysAgo(17), due_date:daysFromNow(10),
    timeline:[
      { action:'Reported via support chat — Eastfield store manager', time:daysAgo(18), author:'James Park' },
      { action:'Initial response: likely display refresh delay — monitoring', time:daysAgo(17), author:'James Park' },
    ],
    comments:[
      { id:'cN2a', author:'James Park', text:'Customer flagged as requiring follow-up but not escalated to leadership. Discrepancy count is small (3 orders) — could be portal caching issue. Finance ops at FreshMart noted it but described as "investigating before raising formally — not yet confirmed as systemic."', time:daysAgo(17), isAI:false },
    ],
  },

  /* === QUARTER === */
  {
    id:'TKT-1006', sentiment_score:2,
    title:'Stale offline pricing synced to orders — distributors invoiced at incorrect rates',
    description:'Orders created offline use price tier cached at app launch. If server-side prices change while rep is offline, synced order carries stale prices. Server accepts client-submitted price without re-validating. AgriSource reported 14 affected orders with $11K pricing discrepancy.',
    priority:'medium', status:'closed', category:'Bug', source:'Email',
    tags:['sync','offline','pricing','data-integrity','billing'],
    assignee:'Riya Patel', customerId:'CUST-005',
    created_at:daysAgo(85), updated_at:daysAgo(82), due_date:daysAgo(79),
    timeline:[
      { action:'Reported by AgriSource account manager Ravi Menon', time:daysAgo(85), author:'Sarah Ali' },
    ],
    comments:[
      { id:'c6a', author:'Riya Patel', text:'Secondary to idempotency cluster but must ship in same release. Server should re-validate price on order receipt. Lower urgency but impacts billing accuracy across all offline-enabled customers.', time:daysAgo(82), isAI:false },
    ],
  },
  {
    id:'TKT-1009', sentiment_score:5,
    title:'Bulk order sync taking 90+ seconds for warehouse batch uploads — SLA breach risk',
    description:'QuickShip uploads 50-80 order batches at shift start. Sequential individual POSTs take 90-120 seconds, exceeding 60-second sync SLA. Fix requires batch sync endpoint. Batch endpoint also needs per-order idempotency keys to prevent duplicates in partial-batch retry scenarios.',
    priority:'medium', status:'resolved', category:'Feature Request', source:'API',
    tags:['sync','offline','performance','batch','warehouse','idempotency-missing'],
    assignee:'Dev Kumar', customerId:'CUST-004',
    created_at:daysAgo(78), updated_at:daysAgo(74), due_date:daysAgo(70),
    timeline:[
      { action:'Raised by QuickShip operations lead Laura Chen', time:daysAgo(78), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c9-health', author:'Platform Health Monitor', text:'SCHEDULED HEALTH CHECK: Sync success rate 97.3% (within SLA threshold of 95%). Average sync latency 4.2s (nominal). No systemic anomalies detected. Batch upload latency flagged as performance optimisation opportunity — not a reliability concern. Overall platform health: STABLE.', time:daysAgo(77), isAI:false },
      { id:'c9-unaffected', author:'Dev Kumar', text:'Note: QuickShip not reporting duplicate order issues at this stage. Warehouse team works primarily in-warehouse with reliable WiFi — offline submissions rare, under 5% of order volume. Duplicate-submit pattern appears triggered specifically by extended offline periods in low-connectivity environments. Issue may not be visible to all customers until offline usage increases.', time:daysAgo(74), isAI:false },
      { id:'c9a', author:'Dev Kumar', text:'Batch endpoint cannot ship without idempotency. If a 30-order batch is partially processed and client retries, we need idempotency keys per order within the batch. Blocked on TKT-1002 fix.', time:daysAgo(74), isAI:false },
    ],
  },
  {
    id:'TKT-1012', sentiment_score:4,
    title:'23 delivery SLA breaches — early sync delay pattern, pre-escalation',
    description:'FreshMart logged 23 SLA breach incidents over 5 days. Orders did not reach warehouse in time for same-day dispatch. Upstream: sync delay from WMS integration timeout. FreshMart requesting $18K SLA credits.',
    priority:'medium', status:'resolved', category:'Incident', source:'Email',
    tags:['sync','sla','delivery','warehouse'],
    assignee:'James Park', customerId:'CUST-002',
    created_at:daysAgo(70), updated_at:daysAgo(67), due_date:daysAgo(64),
    timeline:[
      { action:'Formal SLA breach notification from FreshMart legal', time:daysAgo(70), author:'James Park' },
    ],
    comments:[
      { id:'c12a', author:'James Park', text:'FreshMart legal requesting $18K SLA credit. Sync delay and duplicate order issues being cited together in their August renewal evaluation.', time:daysAgo(67), isAI:false },
    ],
  },
  {
    id:'TKT-1015', sentiment_score:1,
    title:'No notification when offline order permanently fails — reps discover loss when customers complain',
    description:'When sync retry limit exhausted, orders silently dropped with no push notification. Reps discover losses only when customers call about missing deliveries. Silent failure amplified by missing idempotency: reps who retry manually create duplicates, while reps who do not retry lose the order entirely.',
    priority:'medium', status:'resolved', category:'Bug', source:'API',
    tags:['sync','offline','data-loss','notification','retry-loop'],
    assignee:'Dev Kumar', customerId:'CUST-001',
    created_at:daysAgo(52), updated_at:daysAgo(49), due_date:daysAgo(46),
    timeline:[
      { action:'Identified by GlobalFoods field operations manager', time:daysAgo(52), author:'Dev Kumar' },
    ],
    comments:[],
  },
  {
    id:'TKT-1017', sentiment_score:3,
    title:'Distributor portal shows incorrect pending order count during active sync',
    description:'While sync runs, distributor portal displays incorrect pending order count that does not reflect in-transit orders. Distributors acting on incorrect count submit redundant orders — secondary trigger of duplicate-submit pattern at portal layer.',
    priority:'medium', status:'resolved', category:'Bug', source:'Chat',
    tags:['sync','visibility','portal','ui'],
    assignee:'Sarah Ali', customerId:'CUST-005',
    created_at:daysAgo(58), updated_at:daysAgo(55), due_date:daysAgo(50),
    timeline:[
      { action:'Reported via support chat by AgriSource distributor', time:daysAgo(58), author:'Sarah Ali' },
    ],
    comments:[],
  },
  {
    id:'TKT-1019', sentiment_score:2,
    title:'Order export missing failed sync attempts — compliance report blocked',
    description:'Order history export only shows successfully synced orders. Orders that failed during offline sync do not appear in any export. Logix Pharma cannot produce order attempt log for regulatory submission.',
    priority:'medium', status:'resolved', category:'Incident', source:'Email',
    tags:['sync','offline','compliance','audit','export'],
    assignee:'Riya Patel', customerId:'CUST-003',
    created_at:daysAgo(45), updated_at:daysAgo(42), due_date:daysAgo(38),
    timeline:[
      { action:'Linked to TKT-1018 as downstream reporting consequence', time:daysAgo(45), author:'Riya Patel' },
    ],
    comments:[],
  },
  {
    id:'TKT-1022', sentiment_score:3,
    title:'SQLCipher encryption key fails on auth token rotation during offline period',
    description:'When field rep auth token expires during offline shift, SQLCipher encryption key fails on next app open. Local order database cannot be decrypted. No recovery path defined.',
    priority:'medium', status:'resolved', category:'Incident', source:'API',
    tags:['sync','offline','security','encryption','data-loss'],
    assignee:'Dev Kumar', customerId:'CUST-003',
    created_at:daysAgo(65), updated_at:daysAgo(62), due_date:daysAgo(58),
    timeline:[
      { action:'Discovered during Logix Pharma security review', time:daysAgo(65), author:'Dev Kumar' },
      { action:'No migration path confirmed — data loss risk acknowledged', time:daysAgo(62), author:'Dev Kumar' },
    ],
    comments:[
      { id:'c22a', author:'Dev Kumar', text:'Separate failure class from idempotency cluster but same underlying theme: offline sync architecture not designed for failure recovery. Key rotation, idempotency, retry behavior, and audit logging are all gaps in the same offline reliability design.', time:daysAgo(62), isAI:false },
    ],
  },
  {
    id:'TKT-1023', sentiment_score:1,
    title:'Intermittent order delivery delay — logged as isolated incident',
    description:'Single GlobalFoods field rep reported order placed offline did not appear in delivery schedule next morning. She re-entered manually. Duplicate caught by warehouse team and cancelled. Logged as isolated user error.',
    priority:'low', status:'closed', category:'Query', source:'Chat',
    tags:['sync','offline','field-ops'],
    assignee:'Sarah Ali', customerId:'CUST-001',
    created_at:daysAgo(75), updated_at:daysAgo(73), due_date:daysAgo(72),
    timeline:[
      { action:'Ticket created via support chat', time:daysAgo(75), author:'Sarah Ali' },
      { action:'Assessed as isolated user error', time:daysAgo(73), author:'Sarah Ali' },
      { action:'Status changed: open → closed', time:daysAgo(73), author:'Sarah Ali' },
    ],
    comments:[
      { id:'cN1a', author:'Platform Health Monitor', text:'ROUTINE CHECK: No anomalies linked to this ticket. Sync success rate: 97.8%. Classified as user behaviour — not a platform reliability event. Platform health: STABLE.', time:daysAgo(73), isAI:false },
      { id:'cN1b', author:'Sarah Ali', text:'Rep confirmed she was in an area with poor signal. Manual re-entry was caught before causing a problem. Platform health remains stable.', time:daysAgo(72), isAI:false },
    ],
  },
];

window.activityLog = [];
window.tickets.forEach(t => {
  window.activityLog.push({ type:'created', ticketId:t.id,
    text:`Ticket <strong>${t.id}</strong> created — ${t.title.substring(0,60)}...`,
    time:t.created_at });
  t.comments.forEach(c => {
    if (c.author.includes('VP') || c.author.includes('COO') || c.author.includes('CFO') ||
        c.author.includes('Marcus') || c.author.includes('Priya') || c.author.includes('Okafor') ||
        c.author.includes('System Monitor')) {
      window.activityLog.push({ type:'escalation', ticketId:t.id,
        text:`<strong>${c.author.split('(')[0].trim()}</strong> escalated on <strong>${t.id}</strong>`,
        time:c.time });
    }
  });
});
window.activityLog.sort((a,b) => new Date(b.time) - new Date(a.time));
window.ticketCounter = 1025;
window.getCustomer = (id) => window.customers.find(c => c.id === id) || null;
