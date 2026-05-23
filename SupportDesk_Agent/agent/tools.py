"""
tools.py — Rule-based tool implementations
Phase 2: pure Python logic, no LLM
"""

import json
from datetime import datetime
from typing import Any

def load_data():
    with open("data/tickets.json")   as f: tickets   = json.load(f)
    with open("data/customers.json") as f: customers = json.load(f)
    return tickets, customers

def get_customer(customers, customer_id):
    return next((c for c in customers if c["id"] == customer_id), {})

# ── TOOL 1: Analyze Ticket ────────────────────────────────────────

def analyze_ticket(ticket_id: str) -> dict:
    tickets, customers = load_data()
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)

    if not ticket:
        return {
            "error": f"Ticket {ticket_id} not found",
            "hallucination_check": True
        }

    customer = get_customer(customers, ticket["customer_id"])

    # Rule-based severity — no inference, just rules
    priority_score = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    severity       = ticket["priority"]

    # Rule-based root cause — tag matching
    root_cause = "Unable to determine root cause from tags alone"
    tags = ticket.get("tags", [])
    if "idempotency" in tags:
        root_cause = "Missing idempotency key on API requests — duplicates on retry"
    elif "crash" in tags or "data-loss" in tags:
        root_cause = "Application crash corrupting local queue state"
    elif "sync" in tags and "timeout" in tags:
        root_cause = "Sync operation timeout — likely network or backend latency"
    elif "compliance" in tags or "audit" in tags:
        root_cause = "Missing audit trail for regulatory compliance"

    # Rule-based action
    action = "Assign to engineering team for investigation"
    if severity == "critical":
        action = "IMMEDIATE: Escalate to engineering lead and notify CSM"
    elif "churn-risk" in tags or "vp-escalation" in tags:
        action = "URGENT: Notify VP Customer Success within 2 hours"
    elif "billing" in tags:
        action = "Notify finance team + customer CSM within 24 hours"

    return {
        "ticket_id":            ticket_id,
        "title":                ticket["title"],
        "severity_assessment":  severity,
        "status":               ticket["status"],
        "root_cause_hypothesis": root_cause,
        "recommended_action":   action,
        "customer":             customer.get("name", "Unknown"),
        "customer_arr":         customer.get("arr", 0),
        "customer_health":      customer.get("health", 0),
        "tags":                 tags,
        "confidence":           0.4,   # Phase 2 baseline — low confidence
        "evidence":             [f"tags: {tags}", f"priority: {severity}"],
        "hallucination_check":  True,  # all claims from input fields
        "phase":                "baseline_rules"
    }

# ── TOOL 2: Detect Patterns ───────────────────────────────────────

def detect_patterns(window: str = "7d", min_cluster_size: int = 2) -> dict:
    tickets, _ = load_data()
    now        = datetime.now()

    # Filter by time window
    window_days = {"7d": 7, "30d": 30, "90d": 90}.get(window, 7)

    def in_window(ticket):
        try:
            created = datetime.fromisoformat(ticket["created_at"])
            delta   = (now - created).days
            if window == "7d":  return delta <= 7
            if window == "30d": return 7 < delta <= 30
            if window == "90d": return 30 < delta <= 90
        except:
            return False

    windowed = [t for t in tickets if in_window(t)]

    # Count tag frequency across windowed tickets
    tag_counts  = {}
    tag_tickets = {}
    for ticket in windowed:
        for tag in ticket.get("tags", []):
            tag_counts[tag]  = tag_counts.get(tag, 0) + 1
            tag_tickets[tag] = tag_tickets.get(tag, []) + [ticket["id"]]

    # Build clusters — tags appearing in min_cluster_size+ tickets
    patterns = []
    seen_clusters = set()
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        if count < min_cluster_size:
            continue
        cluster_key = tag
        if cluster_key in seen_clusters:
            continue
        seen_clusters.add(cluster_key)

        tids = tag_tickets[tag]
        relevant = [t for t in windowed if t["id"] in tids]
        priorities = [t["priority"] for t in relevant]
        customers  = list(set(t["customer_id"] for t in relevant))

        # Trend: compare first half vs second half of window by created_at
        sorted_tix = sorted(relevant, key=lambda x: x["created_at"])
        mid = len(sorted_tix) // 2
        trend = "stable"
        if len(sorted_tix) >= 4:
            first_half_sev  = sum(1 for t in sorted_tix[:mid]  if t["priority"] in ["critical","high"])
            second_half_sev = sum(1 for t in sorted_tix[mid:]  if t["priority"] in ["critical","high"])
            trend = "accelerating" if second_half_sev > first_half_sev else "declining" if second_half_sev < first_half_sev else "stable"

        patterns.append({
            "tag_cluster":            [tag],
            "ticket_ids":             tids,
            "frequency":              count,
            "severity_distribution":  {p: priorities.count(p) for p in set(priorities)},
            "customer_ids":           customers,
            "trend":                  trend,
            "recommendation":         f"Review all {tag} tickets — {count} occurrences in {window} window",
            "confidence":             0.35,  # Phase 2 — tag matching only
            "phase":                  "baseline_rules"
        })

    return {
        "patterns":               patterns[:5],  # top 5
        "window":                 window,
        "total_tickets_analyzed": len(windowed),
        "hallucination_check":    True
    }

# ── TOOL 3: Predict SLA Risk ──────────────────────────────────────

def predict_sla_risk(lookahead_hours: int = 24) -> dict:
    tickets, customers = load_data()
    now = datetime.now()

    at_risk    = []
    breached   = []
    safe       = []

    for ticket in tickets:
        if ticket["status"] in ["resolved", "closed"]:
            continue
        if not ticket.get("due_date"):
            continue

        try:
            due    = datetime.fromisoformat(ticket["due_date"])
            delta  = (due - now).total_seconds() / 3600  # hours
            customer = get_customer(customers, ticket["customer_id"])

            if delta < 0:
                breached.append(ticket["id"])
            elif delta <= lookahead_hours:
                # Rule: critical tickets are higher breach probability
                prob = 0.9 if ticket["priority"] == "critical" else \
                       0.7 if ticket["priority"] == "high" else 0.4

                at_risk.append({
                    "ticket_id":            ticket["id"],
                    "title":                ticket["title"][:60] + "...",
                    "customer_id":          ticket["customer_id"],
                    "customer_name":        customer.get("name", "Unknown"),
                    "arr":                  customer.get("arr", 0),
                    "hours_until_breach":   round(delta, 1),
                    "breach_probability":   prob,
                    "priority":             ticket["priority"],
                    "reason":               f"Due in {round(delta,1)}h — {ticket['priority']} priority",
                    "recommended_action":   "Assign and begin work immediately" if delta < 4
                                            else "Assign within 2 hours",
                    "confidence":           0.5,
                    "phase":                "baseline_rules"
                })
            else:
                safe.append(ticket["id"])
        except:
            continue

    # Sort at_risk by hours_until_breach ascending
    at_risk.sort(key=lambda x: x["hours_until_breach"])

    return {
        "at_risk":             at_risk,
        "already_breached":    breached,
        "safe":                safe,
        "lookahead_hours":     lookahead_hours,
        "hallucination_check": True
    }

# ── TOOL 4: Rank Customer Risk ────────────────────────────────────

def rank_customer_risk() -> dict:
    tickets, customers = load_data()

    ranked = []
    total_arr_at_risk = 0

    for customer in customers:
        cid         = customer["id"]
        cust_tickets = [t for t in tickets if t["customer_id"] == cid]
        open_tickets = [t for t in cust_tickets if t["status"] not in ["resolved","closed"]]

        critical_count = sum(1 for t in open_tickets if t["priority"] == "critical")
        high_count     = sum(1 for t in open_tickets if t["priority"] == "high")

        # SLA breaches — overdue tickets
        now = datetime.now()
        sla_breaches = 0
        for t in open_tickets:
            try:
                due = datetime.fromisoformat(t["due_date"])
                if due < now: sla_breaches += 1
            except: pass

        # Churn signals from tags
        churn_signals = sum(
            1 for t in open_tickets
            if any(tag in t.get("tags", [])
                   for tag in ["churn-risk", "vp-escalation", "legal", "escalation"])
        )

        # Composite risk score (0–100)
        # Weights: health inverse (40%), critical tickets (25%), ARR magnitude (20%), churn (15%)
        health_risk    = (100 - customer["health"]) * 0.40
        ticket_risk    = min((critical_count * 15 + high_count * 5), 25)
        arr_weight     = min((customer["arr"] / 1500000) * 20, 20)
        churn_weight   = min(churn_signals * 7.5, 15)
        risk_score     = round(health_risk + ticket_risk + arr_weight + churn_weight, 1)

        risk_label = (
            "critical" if risk_score >= 70 else
            "high"     if risk_score >= 50 else
            "medium"   if risk_score >= 30 else "low"
        )

        if risk_label in ["critical", "high"]:
            total_arr_at_risk += customer["arr"]

        # Primary reason — rule-based
        if churn_signals > 0:
            reason = f"{churn_signals} churn-risk signal(s) in open tickets"
        elif critical_count > 0:
            reason = f"{critical_count} critical open ticket(s) unresolved"
        elif sla_breaches > 0:
            reason = f"{sla_breaches} SLA breach(es) recorded"
        else:
            reason = f"Health score {customer['health']}/100 — below threshold"

        ranked.append({
            "customer_id":           cid,
            "name":                  customer["name"],
            "arr":                   customer["arr"],
            "health_score":          customer["health"],
            "open_tickets":          len(open_tickets),
            "open_critical_tickets": critical_count,
            "sla_breach_count":      sla_breaches,
            "churn_signals":         churn_signals,
            "risk_score":            risk_score,
            "risk_label":            risk_label,
            "primary_risk_reason":   reason,
            "recommended_action":    "Executive escalation required" if risk_label == "critical"
                                     else "CSM check-in within 24h" if risk_label == "high"
                                     else "Monitor weekly",
            "confidence":            0.5,
            "phase":                 "baseline_rules"
        })

    ranked.sort(key=lambda x: -x["risk_score"])
    total_arr_at_risk = sum(c["arr"] for c in customers
                            if any(r["customer_id"] == c["id"] and r["risk_label"] in ["critical","high"]
                                   for r in ranked))

    return {
        "ranked_customers":    ranked,
        "total_arr_at_risk":   total_arr_at_risk,
        "hallucination_check": True
    }

# ── TOOL 5: General Summary ───────────────────────────────────────

def general_summary() -> dict:
    tickets, customers = load_data()
    now = datetime.now()

    open_tickets    = [t for t in tickets if t["status"] not in ["resolved","closed"]]
    critical_open   = [t for t in open_tickets if t["priority"] == "critical"]
    high_open       = [t for t in open_tickets if t["priority"] == "high"]

    return {
        "total_tickets":        len(tickets),
        "open_tickets":         len(open_tickets),
        "critical_open":        len(critical_open),
        "high_open":            len(high_open),
        "critical_ticket_ids":  [t["id"] for t in critical_open],
        "top_urgent":           sorted(
                                    open_tickets,
                                    key=lambda t: (
                                        {"critical":0,"high":1,"medium":2,"low":3}[t["priority"]],
                                        t.get("sentiment_score", 5) * -1
                                    )
                                )[:3],
        "recommendation":       f"Address {len(critical_open)} critical tickets immediately",
        "hallucination_check":  True,
        "phase":                "baseline_rules"
    }