"""
rag_agent.py — Phase 4 orchestrator
Location: supportdesk_agent/agent/rag_agent.py

Uses RAG retrieval instead of static data injection.
Same interface as llm_agent: run_rag_agent(query) -> str

Import fix: agent.rag.retriever (not rag.retriever)
because retriever.py lives at agent/rag/retriever.py
"""

import json, re, time
from agent.safety        import check_safety
from agent.intent_router import detect_intent
from agent.logger        import log_interaction
from agent.llm_tools     import call_llm

# ── RAG imports — full path from project root ─────────────────────
from agent.rag.retriever     import (retrieve_tickets,
                                      retrieve_all_customers,
                                      retrieve_sla_at_risk,
                                      retrieve_patterns)
from agent.rag.context_builder import (build_ticket_context,
                                        build_customer_context,
                                        build_sla_context,
                                        build_cross_ticket_context,
                                        get_retrieval_stats)

# ── Prompt templates ──────────────────────────────────────────────
from agent.prompts.v4_rag import (SYSTEM_PROMPT,
                                   analyze_ticket_prompt,
                                   detect_patterns_prompt,
                                   customer_risk_prompt,
                                   sla_risk_prompt,
                                   cross_ticket_prompt)


def extract_ticket_id(query: str):
    match = re.search(r"TKT-\d+", query.upper())
    return match.group() if match else None


def _ensure_list(result: dict, list_key: str) -> list:
    val = result.get(list_key)
    if isinstance(val, list):
        return val
    # LLM returned single object at top level — wrap it
    if list_key == "patterns"         and "pattern_name" in result: return [result]
    if list_key == "ranked_customers" and "customer_id"  in result: return [result]
    if list_key == "at_risk"          and "ticket_id"    in result: return [result]
    return []


def format_rag_response(intent: str, result: dict,
                        retrieval_stats: dict) -> str:
    """Format RAG JSON response into readable terminal output."""

    if "error" in result:
        return f"ERROR: {result['error']}"

    latency   = result.get("latency_ms", 0)
    tokens    = result.get("tokens", 0)
    ret_count = retrieval_stats.get("count", 0)
    ret_avg   = retrieval_stats.get("avg_relevance", 0)
    footer    = (
        f"\n[RAG Phase 4 | {latency}ms | {tokens} tokens | "
        f"Retrieved: {ret_count} docs | Avg relevance: {ret_avg}]"
    )

    # ── Ticket Analysis ────────────────────────────────────────────
    if intent == "analyze_ticket":
        return (
            f"TICKET ANALYSIS (RAG): {result.get('ticket_id','—')}\n{'─'*50}\n"
            f"Root Cause:      {result.get('root_cause_hypothesis','—')}\n"
            f"Severity:        {result.get('severity_assessment','—').upper()}\n"
            f"Business Impact: {result.get('business_impact','—')}\n"
            f"Action:          {result.get('recommended_action','—')}\n"
            f"Confidence:      {result.get('confidence','—')}\n"
            f"Evidence:        {' | '.join(result.get('evidence',[]))}"
            + footer
        )

    # ── Cross-ticket / General Summary ────────────────────────────
    elif intent == "cross_ticket":
        if not result.get("shared_root_cause"):
            return (
                f"CROSS-TICKET ANALYSIS — parse issue\n{'─'*50}\n"
                f"Raw keys: {list(result.keys())}" + footer
            )
        tickets_cited = ", ".join(result.get("supporting_tickets", []))
        evidence      = "\n  • ".join(result.get("evidence", []))
        return (
            f"CROSS-TICKET ANALYSIS (RAG)\n{'─'*50}\n"
            f"Root Cause:\n  {result.get('shared_root_cause','—')}\n\n"
            f"Pattern:\n  {result.get('pattern_description','—')}\n\n"
            f"Supporting Tickets "
            f"({result.get('tickets_analyzed', ret_count)} analyzed): "
            f"{tickets_cited}\n\n"
            f"Business Impact:\n  {result.get('business_impact','—')}\n\n"
            f"Recommended Fix:\n  {result.get('recommended_fix','—')}\n\n"
            f"Evidence:\n  • {evidence}\n\n"
            f"Confidence: {result.get('confidence','—')} | "
            f"Grounded: {result.get('retrieval_grounded', False)}"
            + footer
        )

    # ── Pattern Detection ──────────────────────────────────────────
    elif intent == "detect_patterns":
        patterns = _ensure_list(result, "patterns")
        window   = result.get("window", "7d")
        analyzed = result.get("total_analyzed", ret_count)

        if not patterns:
            return (
                f"PATTERN DETECTION (RAG)\n{'─'*50}\n"
                f"Window: {window} | Tickets retrieved: {analyzed}\n"
                f"No significant patterns found." + footer
            )

        lines = [f"PATTERNS — RAG ({window} | {analyzed} tickets retrieved)\n{'─'*50}"]
        for i, p in enumerate(patterns, 1):
            tags = ", ".join(p.get("tag_cluster", []))
            tids = ", ".join(p.get("ticket_ids", []))
            lines.append(
                f"{i}. {p.get('pattern_name', tags or '—')}\n"
                f"   Tags:       [{tags}]\n"
                f"   Tickets:    {tids or '—'}\n"
                f"   Frequency:  {p.get('frequency','—')}\n"
                f"   Trend:      {p.get('trend','—')}\n"
                f"   Signal:     {p.get('root_cause_signal','—')}\n"
                f"   → Action:   {p.get('recommendation','—')}\n"
                f"   Confidence: {p.get('confidence','—')}\n"
            )
        return "\n".join(lines) + footer

    # ── SLA Risk ───────────────────────────────────────────────────
    elif intent == "predict_sla_risk":
        at_risk        = _ensure_list(result, "at_risk")
        breached_count = result.get("already_breached_count", 0)
        summary        = result.get("risk_summary", "")
        arr_exp        = result.get("total_arr_exposure", 0)

        lines = [f"SLA RISK ASSESSMENT (RAG)\n{'─'*50}"]
        if summary:   lines.append(f"Summary: {summary}\n")
        if arr_exp:   lines.append(f"Total ARR Exposure: ${arr_exp:,}\n")
        if breached_count:
            lines.append(f"⛔ Already breached: {breached_count} tickets\n")
        if at_risk:
            lines.append(f"🔴 At Risk ({len(at_risk)} tickets):")
            for r in at_risk:
                lines.append(
                    f"  {r.get('ticket_id','—')} — "
                    f"{r.get('hours_until_breach','?')}h | "
                    f"prob {r.get('breach_probability','?')}\n"
                    f"  Impact: {r.get('business_impact','—')}\n"
                    f"  → {r.get('recommended_action','—')}"
                )
        if not at_risk and not breached_count:
            lines.append("✅ No SLA breaches detected.")
        return "\n".join(lines) + footer

    # ── Customer Risk Ranking ──────────────────────────────────────
    elif intent == "rank_customer_risk":
        ranked   = _ensure_list(result, "ranked_customers")
        arr_risk = result.get("total_arr_at_risk", 0)
        returned = result.get("customer_count_returned", len(ranked))

        lines = [
            f"CUSTOMER RISK RANKING (RAG)\n{'─'*50}",
            f"Total ARR at risk: ${arr_risk:,} | Customers: {returned}\n"
        ]
        for i, c in enumerate(ranked, 1):
            lines.append(
                f"{i}. {c.get('name','—')} — "
                f"{c.get('risk_label','—').upper()} "
                f"(score: {c.get('risk_score','—')})\n"
                f"   ARR: ${c.get('arr',0):,} | "
                f"Health: {c.get('health_score','—')}/100\n"
                f"   Reason: {c.get('primary_risk_reason','—')}\n"
                f"   → {c.get('recommended_action','—')}\n"
                f"   Confidence: {c.get('confidence','—')}\n"
            )
        return "\n".join(lines) + footer

    # ── Fallback ───────────────────────────────────────────────────
    return json.dumps(result, indent=2) + footer


def run_rag_agent(query: str, verbose: bool = False) -> str:
    start = time.time()

    # Safety — always first
    safety_status, safety_msg = check_safety(query)
    if safety_status == "unsafe":
        return f"🚫 SAFETY BLOCK: {safety_msg}"
    if safety_status == "escalate":
        return f"⚠️  ESCALATION FLAGGED: {safety_msg}"

    # Intent detection
    intent, confidence = detect_intent(query)
    query_lower = query.lower()

    # Override: cross-ticket for queries without explicit ticket ID
    if (intent == "analyze_ticket" and not extract_ticket_id(query)) or \
       any(p in query_lower for p in [
           "root cause across", "common across", "pattern across",
           "keeps going wrong", "what keeps", "why do", "most urgent"
       ]):
        intent = "cross_ticket"

    if verbose:
        print(f"[RAG ROUTER] Intent: {intent} | Confidence: {confidence}")

    result          = {}
    retrieval_stats = {}

    # ── analyze_ticket ─────────────────────────────────────────────
    if intent == "analyze_ticket":
        tid = extract_ticket_id(query)
        if not tid:
            intent = "cross_ticket"
        else:
            docs   = retrieve_tickets(f"ticket {tid}", top_k=3)
            exact  = [d for d in docs if d["id"] == tid]
            docs   = exact if exact else docs[:1]
            ctx    = build_ticket_context(docs, max_docs=1)
            stats  = get_retrieval_stats(docs)
            if verbose:
                print(f"[RAG] {stats['count']} docs | "
                      f"avg relevance: {stats['avg_relevance']}")
            result, latency, tokens = call_llm(
                SYSTEM_PROMPT, analyze_ticket_prompt(ctx, tid)
            )
            if isinstance(result, dict):
                result.update({"latency_ms": round(latency*1000), "tokens": tokens})
            retrieval_stats = stats

    # ── cross_ticket ───────────────────────────────────────────────
    if intent == "cross_ticket":
        docs  = retrieve_tickets(query, window="all", top_k=12)
        ctx   = build_cross_ticket_context(docs, max_docs=12)
        stats = get_retrieval_stats(docs)
        if verbose:
            print(f"[RAG] {stats['count']} docs | "
                  f"avg relevance: {stats['avg_relevance']}")
        result, latency, tokens = call_llm(
            SYSTEM_PROMPT, cross_ticket_prompt(ctx, query, stats["count"])
        )
        if isinstance(result, dict):
            result.update({"latency_ms": round(latency*1000), "tokens": tokens})
        retrieval_stats = stats

    # ── detect_patterns ────────────────────────────────────────────
    elif intent == "detect_patterns":
        window = "7d"
        if "month" in query_lower or "30" in query_lower:  window = "30d"
        if "quarter" in query_lower or "90" in query_lower: window = "90d"
        docs  = retrieve_patterns(window=window, top_k=10)
        ctx   = build_ticket_context(docs, max_docs=10)
        stats = get_retrieval_stats(docs)
        if verbose:
            print(f"[RAG] {stats['count']} docs for {window} | "
                  f"avg relevance: {stats['avg_relevance']}")
        result, latency, tokens = call_llm(
            SYSTEM_PROMPT,
            detect_patterns_prompt(ctx, window, stats["count"])
        )
        if isinstance(result, dict):
            result.update({"latency_ms": round(latency*1000), "tokens": tokens})
        retrieval_stats = stats

    # ── predict_sla_risk ───────────────────────────────────────────
    elif intent == "predict_sla_risk":
        docs  = retrieve_sla_at_risk(lookahead_hours=24)
        ctx   = build_sla_context(docs)
        stats = get_retrieval_stats(docs)
        if verbose:
            print(f"[RAG] {stats['count']} SLA-at-risk docs")
        result, latency, tokens = call_llm(
            SYSTEM_PROMPT, sla_risk_prompt(ctx)
        )
        if isinstance(result, dict):
            result.update({"latency_ms": round(latency*1000), "tokens": tokens})
        retrieval_stats = stats

    # ── rank_customer_risk ─────────────────────────────────────────
    elif intent == "rank_customer_risk":
        docs  = retrieve_all_customers(query)
        ctx   = build_customer_context(docs)
        stats = get_retrieval_stats(docs)
        if verbose:
            print(f"[RAG] {stats['count']} customers retrieved "
                  f"(all guaranteed: {stats['count'] == 5})")
        result, latency, tokens = call_llm(
            SYSTEM_PROMPT, customer_risk_prompt(ctx, stats["count"])
        )
        if isinstance(result, dict):
            result.update({"latency_ms": round(latency*1000), "tokens": tokens})
        retrieval_stats = stats

    # ── general_summary → cross_ticket ────────────────────────────
    elif intent == "general_summary":
        docs  = retrieve_tickets(query, window="7d", top_k=8,
                                 status_in=["open", "in-progress"])
        ctx   = build_cross_ticket_context(docs, max_docs=8)
        stats = get_retrieval_stats(docs)
        result, latency, tokens = call_llm(
            SYSTEM_PROMPT,
            cross_ticket_prompt(ctx, query, stats["count"])
        )
        if isinstance(result, dict):
            result.update({"latency_ms": round(latency*1000), "tokens": tokens})
        retrieval_stats = stats
        intent = "cross_ticket"

    # ── unknown intent ─────────────────────────────────────────────
    elif not result:
        result = {
            "error": (
                "I could not understand that query. "
                "Try: ticket analysis (TKT-XXXX), patterns, "
                "SLA risk, or customer risk ranking."
            ),
            "latency_ms": 0, "tokens": 0
        }
        retrieval_stats = {"count": 0, "avg_relevance": 0}

    # ── Log + format ───────────────────────────────────────────────
    total_latency = time.time() - start
    response      = format_rag_response(intent, result, retrieval_stats)

    log_interaction(
        query=query, intent=intent, tool=f"rag_{intent}",
        response=result, latency=total_latency,
        phase="phase4_rag",
        notes=(
            f"retrieved:{retrieval_stats.get('count',0)} "
            f"avg_rel:{retrieval_stats.get('avg_relevance',0)}"
        )
    )

    if verbose:
        print(
            f"[RAG LOGGER] Total: {round(total_latency*1000)}ms | "
            f"LLM: {result.get('latency_ms',0)}ms | "
            f"Tokens: {result.get('tokens',0)} | "
            f"Retrieved: {retrieval_stats.get('count',0)} docs"
        )

    return response
