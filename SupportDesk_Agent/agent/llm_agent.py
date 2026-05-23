"""
llm_agent.py — Phase 3 orchestrator
Replaces baseline_agent.py for Phase 3+ runs
Same interface: run_agent(query) → str
"""

import json, re, time
from agent.safety        import check_safety
from agent.intent_router import detect_intent
from agent.logger        import log_interaction
from agent.llm_tools     import (
    llm_analyze_ticket, llm_detect_patterns,
    llm_cross_ticket_analysis, llm_rank_customer_risk,
    llm_predict_sla_risk
)

DEFAULT_STRATEGY = "v2"   # ← We will justify this after comparison

def extract_ticket_id(query: str):
    match = re.search(r"TKT-\d+", query.upper())
    return match.group() if match else None

def _ensure_list(result: dict, list_key: str) -> list:
    """
    Handles both response shapes:
      Shape A (correct): {"patterns": [...]}       → result.get("patterns")
      Shape B (LLM drift): {"pattern_name": "..."}  → wrap result in a list
    """
    val = result.get(list_key)
    if isinstance(val, list):
        return val
    # LLM returned a single object at top level — wrap it
    if list_key == "patterns" and "pattern_name" in result:
        return [result]
    if list_key == "ranked_customers" and "customer_id" in result:
        return [result]
    if list_key == "at_risk" and "ticket_id" in result:
        return [result]
    return []


def format_llm_response(intent: str, result: dict) -> str:
    """Format LLM JSON into readable terminal output."""

    if "error" in result and "fallback" not in result:
        return f"ERROR: {result['error']}"

    strategy = result.get("strategy", "v2")
    latency  = result.get("latency_ms", 0)
    tokens   = result.get("tokens", 0)
    footer   = f"\n[Strategy: {strategy} | {latency}ms | {tokens} tokens | Phase 3 LLM]"

    # ── Ticket Analysis ────────────────────────────────────────────
    if intent == "analyze_ticket":
        return (
            f"TICKET ANALYSIS: {result.get('ticket_id', '—')}\n{'─'*50}\n"
            f"Root Cause:      {result.get('root_cause_hypothesis', '—')}\n"
            f"Severity:        {result.get('severity_assessment', '—').upper()}\n"
            f"Business Impact: {result.get('business_impact', '—')}\n"
            f"Action:          {result.get('recommended_action', '—')}\n"
            f"Confidence:      {result.get('confidence', '—')}\n"
            f"Evidence:        {' | '.join(result.get('evidence', []))}"
            + footer
        )

    # ── Cross-ticket Analysis (Q1 general + Q5 root cause) ────────
    elif intent == "cross_ticket":
        # Validate the key field exists — if not, the LLM returned something wrong
        if not result.get("shared_root_cause"):
            return (
                f"CROSS-TICKET ANALYSIS — parse incomplete\n{'─'*50}\n"
                f"Raw keys received: {list(result.keys())}\n"
                f"Check logs for full response."
                + footer
            )
        tickets_cited = ", ".join(result.get("supporting_tickets", []))
        evidence      = "\n  • ".join(result.get("evidence", []))
        return (
            f"CROSS-TICKET ANALYSIS\n{'─'*50}\n"
            f"Root Cause:\n  {result.get('shared_root_cause', '—')}\n\n"
            f"Pattern:\n  {result.get('pattern_description', '—')}\n\n"
            f"Supporting Tickets: {tickets_cited}\n\n"
            f"Business Impact:\n  {result.get('business_impact', '—')}\n\n"
            f"Recommended Fix:\n  {result.get('recommended_fix', '—')}\n\n"
            f"Evidence:\n  • {evidence}\n\n"
            f"Confidence: {result.get('confidence', '—')}"
            + footer
        )

    # ── Pattern Detection ──────────────────────────────────────────
    elif intent == "detect_patterns":
        patterns = _ensure_list(result, "patterns")
        window   = result.get("window", "7d")
        analyzed = result.get("total_analyzed",
                   result.get("total_tickets_analyzed", "?"))

        if not patterns:
            return (
                f"PATTERN DETECTION — no patterns found\n{'─'*50}\n"
                f"Window: {window} | Tickets analyzed: {analyzed}\n"
                f"No significant recurring patterns in this time window."
                + footer
            )

        lines = [f"PATTERNS ({window} | {analyzed} tickets analyzed)\n{'─'*50}"]
        for i, p in enumerate(patterns, 1):
            tags    = ", ".join(p.get("tag_cluster", []))
            tids    = ", ".join(p.get("ticket_ids", []))
            lines.append(
                f"{i}. {p.get('pattern_name', tags or '—')}\n"
                f"   Tags:       [{tags}]\n"
                f"   Tickets:    {tids or '—'}\n"
                f"   Frequency:  {p.get('frequency', '—')}\n"
                f"   Trend:      {p.get('trend', '—')}\n"
                f"   Signal:     {p.get('root_cause_signal', '—')}\n"
                f"   → Action:   {p.get('recommendation', '—')}\n"
                f"   Confidence: {p.get('confidence', '—')}\n"
            )
        return "\n".join(lines) + footer

    # ── SLA Risk ───────────────────────────────────────────────────
    elif intent == "predict_sla_risk":
        at_risk  = _ensure_list(result, "at_risk")
        breached = result.get("already_breached", [])
        summary  = result.get("risk_summary", "")
        arr_exp  = result.get("total_arr_exposure", 0)

        lines = [f"SLA RISK ASSESSMENT (LLM-enhanced)\n{'─'*50}"]
        if summary:
            lines.append(f"Summary: {summary}\n")
        if arr_exp:
            lines.append(f"Total ARR Exposure: ${arr_exp:,}\n")
        if breached:
            lines.append(f"⛔ Already Breached: {', '.join(breached)}\n")
        if at_risk:
            lines.append(f"🔴 At Risk ({len(at_risk)} tickets):")
            for r in at_risk:
                hours = r.get("hours_until_breach", "?")
                prob  = r.get("breach_probability", "?")
                lines.append(
                    f"  {r.get('ticket_id', '—')} — "
                    f"{hours}h remaining | prob {prob}\n"
                    f"  Impact: {r.get('business_impact', '—')}\n"
                    f"  → {r.get('recommended_action', '—')}\n"
                    f"  Confidence: {r.get('confidence', '—')}"
                )
        if not at_risk and not breached:
            lines.append("✅ No SLA breaches predicted in the next 24 hours.")
        return "\n".join(lines) + footer

    # ── Customer Risk Ranking ──────────────────────────────────────
    elif intent == "rank_customer_risk":
        ranked  = _ensure_list(result, "ranked_customers")
        arr_risk = result.get("total_arr_at_risk", 0)

        if not ranked:
            return (
                f"CUSTOMER RISK RANKING — parse issue\n{'─'*50}\n"
                f"Raw keys: {list(result.keys())}"
                + footer
            )

        lines = [
            f"CUSTOMER RISK RANKING\n{'─'*50}",
            f"Total ARR at risk: ${arr_risk:,}\n"
        ]
        for i, c in enumerate(ranked, 1):
            lines.append(
                f"{i}. {c.get('name', '—')} — "
                f"{c.get('risk_label', '—').upper()} "
                f"(score: {c.get('risk_score', '—')})\n"
                f"   ARR: ${c.get('arr', 0):,} | "
                f"Health: {c.get('health_score', '—')}/100\n"
                f"   Reason: {c.get('primary_risk_reason', '—')}\n"
                f"   → {c.get('recommended_action', '—')}\n"
                f"   Confidence: {c.get('confidence', '—')}\n"
            )
        return "\n".join(lines) + footer

    # ── Fallback ───────────────────────────────────────────────────
    return json.dumps(result, indent=2) + footer


def run_llm_agent(query: str, strategy: str = DEFAULT_STRATEGY,
                  verbose: bool = False) -> str:
    start = time.time()

    # Safety first — always
    safety_status, safety_msg = check_safety(query)
    if safety_status == "unsafe":
        log_interaction(query, "blocked", "none",
                        {"error": safety_msg}, time.time()-start,
                        phase="phase3_llm")
        return f"🚫 SAFETY BLOCK: {safety_msg}"
    if safety_status == "escalate":
        log_interaction(query, "escalate", "safe_escalate",
                        {"message": safety_msg}, time.time()-start,
                        phase="phase3_llm")
        return f"⚠️  ESCALATION FLAGGED: {safety_msg}"

    # Intent detection — same keyword router as Phase 2
    intent, confidence = detect_intent(query)

    # Override: cross-ticket queries that Phase 2 failed on
    query_lower = query.lower()
    if (intent == "analyze_ticket" and not extract_ticket_id(query)) or \
       any(phrase in query_lower for phrase in
           ["root cause across", "common across", "pattern across",
            "keeps going wrong", "what keeps", "why do"]):
        intent = "cross_ticket"

    if verbose:
        print(f"[ROUTER] Intent: {intent} | Confidence: {confidence} | Strategy: {strategy}")

    # Route to LLM tool
    result = {}
    tool_name = intent

    if intent == "analyze_ticket":
        tid = extract_ticket_id(query)
        if not tid:
            intent = "cross_ticket"
            result = llm_cross_ticket_analysis(query, strategy)
        else:
            result = llm_analyze_ticket(tid, strategy)

    elif intent == "cross_ticket":
        result = llm_cross_ticket_analysis(query, strategy)

    elif intent == "detect_patterns":
        window = "7d"
        if "month" in query_lower or "30" in query: window = "30d"
        if "quarter" in query_lower or "90" in query: window = "90d"
        result = llm_detect_patterns(window, strategy)

    elif intent == "predict_sla_risk":
        result = llm_predict_sla_risk(strategy)

    elif intent == "rank_customer_risk":
        result = llm_rank_customer_risk(strategy)

    elif intent == "general_summary":
        # General summary — use cross-ticket for LLM enrichment
        result = llm_cross_ticket_analysis(
            "What are the most urgent issues right now and why?", strategy
        )
        intent = "cross_ticket"

    else:
        result = {
            "error": "I could not understand that query.",
            "suggestion": "Try: ticket analysis, patterns, SLA risk, customer risk ranking.",
            "phase": "llm_phase3"
        }

    latency  = time.time() - start
    response = format_llm_response(intent, result)

    log_interaction(
        query=query, intent=intent, tool=tool_name,
        response=result, latency=latency,
        phase=f"phase3_llm_{strategy}"
    )

    if verbose:
        total_latency = result.get("latency_ms", round(latency*1000))
        print(f"[LOGGER] Total: {round(latency*1000)}ms | "
              f"LLM: {total_latency}ms | Tokens: {result.get('tokens',0)}")

    return response