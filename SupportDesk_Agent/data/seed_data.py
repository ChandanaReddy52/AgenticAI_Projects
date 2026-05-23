# run this file once to generate data files
# data/seed_data.py

import json, os
from datetime import datetime, timedelta

def days_ago(n):
    return (datetime.now() - timedelta(days=n)).isoformat()

def hours_ago(n):
    return (datetime.now() - timedelta(hours=n)).isoformat()

tickets = [
    # WEEK window — open/in-progress
    {
        "id": "TKT-1001", "sentiment_score": 8,
        "title": "App crash on network reconnect corrupts order queue",
        "description": "Field reps offline 2+ hours see silent crash on reconnect. Pending orders lost. Root cause: NetworkManager fires before DNS resolves.",
        "priority": "high", "status": "open", "category": "Incident",
        "tags": ["sync", "crash", "offline", "data-loss"],
        "assignee": "Dev Kumar", "customer_id": "CUST-001",
        "created_at": hours_ago(36), "updated_at": hours_ago(4),
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    },
    {
        "id": "TKT-1002", "sentiment_score": 9,
        "title": "Duplicate orders after reconnect — POST /api/orders missing Idempotency-Key",
        "description": "Sync queue retries POST without idempotency key. Server creates duplicate order every retry. $42K billing discrepancy at FreshMart.",
        "priority": "critical", "status": "in-progress", "category": "Incident",
        "tags": ["sync", "duplicate", "offline", "idempotency", "billing"],
        "assignee": "Dev Kumar", "customer_id": "CUST-002",
        "created_at": hours_ago(42), "updated_at": hours_ago(2),
        "due_date": datetime.now().isoformat()
    },
    {
        "id": "TKT-1003", "sentiment_score": 7,
        "title": "Orders missing from warehouse queue after partial sync failure",
        "description": "31 missing orders discovered when distributor called. WMS integration callback fails silently.",
        "priority": "high", "status": "open", "category": "Incident",
        "tags": ["sync", "offline", "missing-orders", "warehouse"],
        "assignee": "Riya Patel", "customer_id": "CUST-001",
        "created_at": hours_ago(28), "updated_at": hours_ago(6),
        "due_date": datetime.now().isoformat()
    },
    {
        "id": "TKT-1004", "sentiment_score": 5,
        "title": "FreshMart billed twice — $42K duplicate billing across 12 stores",
        "description": "Same purchase order invoiced twice. Financial reconciliation blocked before month-end.",
        "priority": "high", "status": "open", "category": "Incident",
        "tags": ["sync", "duplicate", "billing", "finance"],
        "assignee": "James Park", "customer_id": "CUST-002",
        "created_at": hours_ago(20), "updated_at": hours_ago(3),
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    },
    {
        "id": "TKT-1016", "sentiment_score": 4,
        "title": "Order shown Confirmed before sync completes — trust breakdown",
        "description": "Optimistic UI update marks orders Confirmed before backend sync. When sync fails buyer sees confirmed order that does not exist.",
        "priority": "high", "status": "open", "category": "Bug",
        "tags": ["sync", "offline", "ux", "trust"],
        "assignee": "Sarah Ali", "customer_id": "CUST-002",
        "created_at": hours_ago(30), "updated_at": hours_ago(8),
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    },
    {
        "id": "TKT-1018", "sentiment_score": 6,
        "title": "Audit logs missing for failed offline transactions — SOX compliance gap",
        "description": "Logix Pharma GxP + SOX requires complete audit trail. Failed offline orders have no log record. Q3 regulatory audit in 14 days.",
        "priority": "high", "status": "open", "category": "Incident",
        "tags": ["sync", "offline", "audit", "compliance", "sox"],
        "assignee": "Sarah Ali", "customer_id": "CUST-003",
        "created_at": hours_ago(40), "updated_at": hours_ago(10),
        "due_date": (datetime.now() + timedelta(days=12)).isoformat()
    },
    {
        "id": "TKT-1020", "sentiment_score": 8,
        "title": "GlobalFoods VP formal notice — platform rollout paused",
        "description": "VP Operations formal notice pausing rollout to 4 regions. 6 open tickets, 31 missing orders, 18 lost orders cited. $800K incremental ARR at risk.",
        "priority": "critical", "status": "open", "category": "Incident",
        "tags": ["sync", "offline", "escalation", "churn-risk", "vp-escalation"],
        "assignee": "Sarah Ali", "customer_id": "CUST-001",
        "created_at": hours_ago(18), "updated_at": hours_ago(2),
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    },
    {
        "id": "TKT-1021", "sentiment_score": 4,
        "title": "FreshMart SLA credit claim $18K — August renewal at risk",
        "description": "FreshMart legal submitted formal SLA credit claim for 23 delivery breaches at $800 per incident.",
        "priority": "high", "status": "open", "category": "Incident",
        "tags": ["sync", "offline", "sla-credit", "legal", "churn-risk"],
        "assignee": "James Park", "customer_id": "CUST-002",
        "created_at": hours_ago(22), "updated_at": hours_ago(5),
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    },
    # MONTH window — mix of resolved and in-progress
    {
        "id": "TKT-1005", "sentiment_score": 7,
        "title": "Orders permanently lost when sync retry limit exhausted",
        "description": "After 5 retries, sync client drops orders silently. No notification. 18 confirmed lost orders.",
        "priority": "high", "status": "resolved", "category": "Incident",
        "tags": ["sync", "offline", "data-loss", "retry-loop"],
        "assignee": "Dev Kumar", "customer_id": "CUST-001",
        "created_at": days_ago(12), "updated_at": days_ago(10),
        "due_date": days_ago(9)
    },
    {
        "id": "TKT-1007", "sentiment_score": 4,
        "title": "iOS background sync killed — BGProcessingTask 30s limit",
        "description": "Order backlogs over 30 items cannot complete within iOS BGProcessingTask 30-second window.",
        "priority": "high", "status": "in-progress", "category": "Bug",
        "tags": ["sync", "offline", "ios", "background-sync"],
        "assignee": "Riya Patel", "customer_id": "CUST-001",
        "created_at": days_ago(28), "updated_at": days_ago(24),
        "due_date": days_ago(20)
    },
    {
        "id": "TKT-1010", "sentiment_score": 8,
        "title": "Field reps in rural zones — 40% sync failure rate",
        "description": "Reps retry manually 2-3 times. Without idempotency keys each retry is a new POST creating duplicate orders.",
        "priority": "high", "status": "in-progress", "category": "Bug",
        "tags": ["sync", "offline", "duplicate", "retry-loop", "idempotency"],
        "assignee": "Riya Patel", "customer_id": "CUST-001",
        "created_at": days_ago(22), "updated_at": days_ago(18),
        "due_date": days_ago(16)
    },
    {
        "id": "TKT-1011", "sentiment_score": 5,
        "title": "WMS integration timing out on high-volume sync days",
        "description": "QuickShip WMS integration times out over 100 orders/hour. Callback failure causes duplicate dispatch entries.",
        "priority": "high", "status": "in-progress", "category": "Incident",
        "tags": ["sync", "duplicate", "warehouse", "integration", "timeout"],
        "assignee": "James Park", "customer_id": "CUST-004",
        "created_at": days_ago(20), "updated_at": days_ago(17),
        "due_date": days_ago(13)
    },
    {
        "id": "TKT-1013", "sentiment_score": 1,
        "title": "Buyers re-submitting orders — no sync status visible",
        "description": "Store buyers cannot tell if offline order has been synced. Tap Submit twice. Each re-submission fires new POST without idempotency key.",
        "priority": "medium", "status": "resolved", "category": "Feature Upgrade",
        "tags": ["sync", "duplicate", "offline", "ux", "visibility"],
        "assignee": "Sarah Ali", "customer_id": "CUST-002",
        "created_at": days_ago(15), "updated_at": days_ago(12),
        "due_date": days_ago(9)
    },
    {
        "id": "TKT-1014", "sentiment_score": 3,
        "title": "Inventory misalignment at AgriSource — duplicate orders causing false stock locks",
        "description": "Duplicate orders processed by inventory reservation before duplicates caught. AgriSource over-reserving stock.",
        "priority": "medium", "status": "in-progress", "category": "Incident",
        "tags": ["sync", "duplicate", "offline", "inventory"],
        "assignee": "Riya Patel", "customer_id": "CUST-005",
        "created_at": days_ago(18), "updated_at": days_ago(15),
        "due_date": days_ago(12)
    },
    # QUARTER window — resolved/closed
    {
        "id": "TKT-1006", "sentiment_score": 2,
        "title": "Stale offline pricing synced — distributors invoiced at incorrect rates",
        "description": "Orders created offline use price cached at app launch. Server accepts without re-validating. $11K pricing discrepancy.",
        "priority": "medium", "status": "closed", "category": "Bug",
        "tags": ["sync", "offline", "pricing", "billing"],
        "assignee": "Riya Patel", "customer_id": "CUST-005",
        "created_at": days_ago(85), "updated_at": days_ago(82),
        "due_date": days_ago(79)
    },
    {
        "id": "TKT-1009", "sentiment_score": 5,
        "title": "Bulk order sync taking 90+ seconds — SLA breach risk",
        "description": "QuickShip uploads 50-80 orders at shift start. Sequential POSTs take 90-120 seconds exceeding 60-second SLA.",
        "priority": "medium", "status": "resolved", "category": "Feature Request",
        "tags": ["sync", "offline", "performance", "batch", "warehouse"],
        "assignee": "Dev Kumar", "customer_id": "CUST-004",
        "created_at": days_ago(78), "updated_at": days_ago(74),
        "due_date": days_ago(70)
    },
    {
        "id": "TKT-1012", "sentiment_score": 4,
        "title": "23 delivery SLA breaches — early sync delay pattern",
        "description": "FreshMart logged 23 SLA breach incidents over 5 days. Sync delay from WMS integration timeout.",
        "priority": "medium", "status": "resolved", "category": "Incident",
        "tags": ["sync", "sla", "delivery", "warehouse"],
        "assignee": "James Park", "customer_id": "CUST-002",
        "created_at": days_ago(70), "updated_at": days_ago(67),
        "due_date": days_ago(64)
    },
    {
        "id": "TKT-1015", "sentiment_score": 1,
        "title": "No notification when offline order permanently fails",
        "description": "Sync retry limit exhausted — orders silently dropped. Reps discover loss when customers call. 18+ confirmed lost orders.",
        "priority": "medium", "status": "resolved", "category": "Bug",
        "tags": ["sync", "offline", "data-loss", "notification"],
        "assignee": "Dev Kumar", "customer_id": "CUST-001",
        "created_at": days_ago(52), "updated_at": days_ago(49),
        "due_date": days_ago(46)
    },
    {
        "id": "TKT-1017", "sentiment_score": 3,
        "title": "Distributor portal shows incorrect pending order count during sync",
        "description": "Portal displays incorrect count during sync. Distributors submit redundant orders.",
        "priority": "medium", "status": "resolved", "category": "Bug",
        "tags": ["sync", "visibility", "portal", "ui"],
        "assignee": "Sarah Ali", "customer_id": "CUST-005",
        "created_at": days_ago(58), "updated_at": days_ago(55),
        "due_date": days_ago(50)
    },
    {
        "id": "TKT-1019", "sentiment_score": 2,
        "title": "Order export missing failed sync attempts — compliance report blocked",
        "description": "Order history export only shows successfully synced orders. Logix Pharma cannot produce order attempt log for regulatory submission.",
        "priority": "medium", "status": "resolved", "category": "Incident",
        "tags": ["sync", "offline", "compliance", "audit", "export"],
        "assignee": "Riya Patel", "customer_id": "CUST-003",
        "created_at": days_ago(45), "updated_at": days_ago(42),
        "due_date": days_ago(38)
    },
    {
        "id": "TKT-1022", "sentiment_score": 3,
        "title": "SQLCipher encryption key fails on auth token rotation during offline",
        "description": "Auth token expires during offline shift. SQLCipher key fails on next app open. Local order database inaccessible.",
        "priority": "medium", "status": "resolved", "category": "Incident",
        "tags": ["sync", "offline", "security", "encryption", "data-loss"],
        "assignee": "Dev Kumar", "customer_id": "CUST-003",
        "created_at": days_ago(65), "updated_at": days_ago(62),
        "due_date": days_ago(58)
    },
    {
        "id": "TKT-1023", "sentiment_score": 1,
        "title": "Intermittent order delivery delay — logged as isolated incident",
        "description": "Single field rep reported order not in delivery schedule. Re-entered manually. Duplicate caught by warehouse.",
        "priority": "low", "status": "closed", "category": "Query",
        "tags": ["sync", "offline", "field-ops"],
        "assignee": "Sarah Ali", "customer_id": "CUST-001",
        "created_at": days_ago(75), "updated_at": days_ago(73),
        "due_date": days_ago(72)
    },
    {
        "id": "TKT-1024", "sentiment_score": 2,
        "title": "FreshMart store manager reports unexplained order count discrepancy",
        "description": "Portal showing 3 fewer pending orders than team activity log. Raised informally. No formal investigation opened.",
        "priority": "medium", "status": "resolved", "category": "Query",
        "tags": ["sync", "visibility", "ux"],
        "assignee": "James Park", "customer_id": "CUST-002",
        "created_at": days_ago(18), "updated_at": days_ago(17),
        "due_date": (datetime.now() + timedelta(days=10)).isoformat()
    }
]

customers = [
    {"id": "CUST-001", "name": "GlobalFoods HQ",        "arr": 1200000, "health": 40,
     "industry": "Food Distribution", "plan": "Enterprise", "csm": "Sarah Ali",
     "contact": "Marcus Webb", "since": "2022-04-10"},
    {"id": "CUST-002", "name": "FreshMart Retail Group", "arr": 1500000, "health": 35,
     "industry": "Retail Chain",      "plan": "Enterprise", "csm": "James Park",
     "contact": "Priya Nair",  "since": "2021-09-01"},
    {"id": "CUST-003", "name": "Logix Pharma Supply",    "arr": 700000,  "health": 55,
     "industry": "Pharma Logistics",  "plan": "Enterprise", "csm": "Riya Patel",
     "contact": "Dr. Okafor",  "since": "2023-01-15"},
    {"id": "CUST-004", "name": "QuickShip Warehousing",  "arr": 500000,  "health": 72,
     "industry": "3PL Logistics",     "plan": "Business",   "csm": "Dev Kumar",
     "contact": "Laura Chen",  "since": "2023-06-20"},
    {"id": "CUST-005", "name": "AgriSource Suppliers",   "arr": 900000,  "health": 68,
     "industry": "Supplier Network",  "plan": "Enterprise", "csm": "Sarah Ali",
     "contact": "Ravi Menon",  "since": "2022-11-03"},
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = BASE_DIR  # since seed_data.py is already inside /data

os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "tickets.json"), "w") as f:
    json.dump(tickets, f, indent=2)

with open(os.path.join(DATA_DIR, "customers.json"), "w") as f:
    json.dump(customers, f, indent=2)