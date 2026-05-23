"""
baseline_agent.py — Phase 2 core orchestrator
Rules + templates only. No LLM.
"""

import json, re, time
from agent.safety       import check_safety
from agent.intent_router import detect_intent
from agent.tools        import (analyze_ticket, detect_patterns,
                                predict_sla_risk, rank_customer_risk,
                                general_summary)
from agent.logger       import log_interaction

def extract_ticket_id(query: str) -> str | None:
    match = re.search(r"TKT-\d+", query.upper())
    return match.group() if match else None

def format_response(intent: str, result: dict) -> str:
    """
    Rule-based text formatter — no LLM.
    Phase 2 limitation: responses are mechanical, not contextual.
    """
    if "error" in result:
        return f"ERROR: {result['error']}"

    if intent == "analyze_ticket":
        return (
            f"TICKET ANALYSIS: {result['ticket_id']}\n"
            f"{'─'*50}\n"
            f"Severity:      {result['severity_assessment'].upper()}\n"
            f"Status:        {result['status']}\n"
            f"Root Cause:    {result['root_cause_hypothesis']}\n"
            f"Action:        {result['recommended_action']}\n"
            f"Customer:      {result['customer']} "
            f"(ARR: ${result['customer_arr']:,} | Health: {result['customer_health']}/100)\n"
            f"Evidence:      {', '.join(result['evidence'])}\n"
            f"Confidence:    {result['confidence']} (Phase 2 — rule-based)\n"
        )

    elif intent == "detect_patterns":
        if not result["patterns"]:
            return f"No patterns detected in {result['window']} window with minimum cluster size 2."
        lines = [f"PATTERNS DETECTED ({result['window']} window — "
                 f"{result['total_tickets_analyzed']} tickets analyzed)\n{'─'*50}"]
        for i, p in enumerate(result["patterns"], 1):
            lines.append(
                f"{i}. Tag: [{', '.join(p['tag_cluster'])}]\n"
                f"   Tickets: {', '.join(p['ticket_ids'])}\n"
                f"   Frequency: {p['frequency']} | Trend: {p['trend']}\n"
                f"   Customers: {', '.join(p['customer_ids'])}\n"
                f"   → {p['recommendation']}\n"
            )
        return "\n".join(lines)

    elif intent == "predict_sla_risk":
        lines = [f"SLA RISK ASSESSMENT (next {result['lookahead_hours']}h)\n{'─'*50}"]
        if result["already_breached"]:
            lines.append(f"⛔ ALREADY BREACHED: {', '.join(result['already_breached'])}")
        if result["at_risk"]:
            lines.append(f"\n🔴 AT RISK ({len(result['at_risk'])} tickets):")
            for r in result["at_risk"]:
                lines.append(
                    f"  {r['ticket_id']} — {r['hours_until_breach']}h remaining\n"
                    f"  Customer: {r['customer_name']} (ARR: ${r['arr']:,})\n"
                    f"  Breach probability: {r['breach_probability']}\n"
                    f"  → {r['recommended_action']}"
                )
        if not result["at_risk"] and not result["already_breached"]:
            lines.append("✅ No SLA breaches predicted in lookahead window.")
        return "\n".join(lines)

    elif intent == "rank_customer_risk":
        lines = [f"CUSTOMER RISK RANKING\n{'─'*50}",
                 f"Total ARR at risk: ${result['total_arr_at_risk']:,}\n"]
        for i, c in enumerate(result["ranked_customers"], 1):
            lines.append(
                f"{i}. {c['name']} — {c['risk_label'].upper()} (score: {c['risk_score']})\n"
                f"   ARR: ${c['arr']:,} | Health: {c['health_score']}/100\n"
                f"   Open: {c['open_tickets']} tickets | Critical: {c['open_critical_tickets']}\n"
                f"   Reason: {c['primary_risk_reason']}\n"
                f"   → {c['recommended_action']}\n"
            )
        return "\n".join(lines)

    elif intent == "general_summary":
        t = result
        top_ids = [tk["id"] for tk in t.get("top_urgent", [])]
        return (
            f"QUEUE SUMMARY\n{'─'*50}\n"
            f"Total tickets: {t['total_tickets']} | "
            f"Open: {t['open_tickets']} | "
            f"Critical: {t['critical_open']} | "
            f"High: {t['high_open']}\n"
            f"Top urgent: {', '.join(top_ids)}\n"
            f"Recommendation: {t['recommendation']}\n"
        )

    return json.dumps(result, indent=2)


def run_agent(query: str, verbose: bool = False) -> str:
    start = time.time()

    # ── Step 1: Safety check ──────────────────────────────────
    safety_status, safety_msg = check_safety(query)
    if safety_status == "unsafe":
        log_interaction(query, "blocked", "none", {"error": safety_msg}, time.time()-start)
        return f"🚫 SAFETY BLOCK: {safety_msg}"
    if safety_status == "escalate":
        log_interaction(query, "escalate", "safe_escalate", {"message": safety_msg}, time.time()-start)
        return f"⚠️  ESCALATION FLAGGED: {safety_msg}"

    # ── Step 2: Intent detection ──────────────────────────────
    intent, confidence = detect_intent(query)

    if verbose:
        print(f"\n[ROUTER] Intent: {intent} | Confidence: {confidence}")

    # ── Step 3: Route to tool ─────────────────────────────────
    tool_name = intent
    result    = {}

    if intent == "analyze_ticket":
        ticket_id = extract_ticket_id(query)
        if not ticket_id:
            result = {"error": "No ticket ID found in query. Please include a ticket ID like TKT-1002."}
        else:
            result = analyze_ticket(ticket_id)

    elif intent == "detect_patterns":
        # Extract window from query
        window = "7d"
        if "month" in query.lower() or "30" in query:  window = "30d"
        if "quarter" in query.lower() or "90" in query: window = "90d"
        result = detect_patterns(window=window)

    elif intent == "predict_sla_risk":
        result = predict_sla_risk(lookahead_hours=24)

    elif intent == "rank_customer_risk":
        result = rank_customer_risk()

    elif intent == "general_summary":
        result = general_summary()

    else:
        result = {
            "error":   "I could not understand that query.",
            "suggestion": "Try asking about: ticket analysis, patterns, SLA risk, or customer risk ranking.",
            "phase":   "baseline_rules"
        }
        tool_name = "unknown"

    # ── Step 4: Format + log ──────────────────────────────────
    latency  = time.time() - start
    response = format_response(intent, result)

    log_interaction(
        query=query, intent=intent, tool=tool_name,
        response=result, latency=latency
    )

    if verbose:
        print(f"[LOGGER] Latency: {round(latency*1000)}ms | "
              f"Grounded: {result.get('hallucination_check', False)}")

    return response