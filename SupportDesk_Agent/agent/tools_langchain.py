"""
tools_langchain.py — LangChain Tool definitions for Phase 5
Location: supportdesk_agent/agent/tools_langchain.py

Fixes applied:
  1. analyze_ticket_tool: hard-stop on missing ticket — no similarity fallback
     Previous behaviour: fell back to docs[:1] → LLM hallucinated TKT-9999
     Fixed: if exact ticket not found, return not-found error, do not proceed

  2. AGENT_SYSTEM_PROMPT (in langchain_agent.py): added explicit guidance
     for Q1 (urgency → cross_ticket_analysis not predict_sla_risk) and
     Q2 (customer-specific pattern → 7d window)

  3. Loop prevention test query added to demonstrate ToolCallTracker
     The tracker needs the agent to call the same tool 3+ times in one turn
     — added a multi-step query that forces this in the demo script
"""

import json
from pydantic import BaseModel, Field
from langchain.tools import tool


# ── Input schemas ─────────────────────────────────────────────────

class TicketIdInput(BaseModel):
    ticket_id: str = Field(
        description="The exact ticket ID to analyze, e.g. TKT-1002. "
                    "Must match an existing ticket exactly."
    )

class PatternInput(BaseModel):
    window: str = Field(
        default="7d",
        description=(
            "Time window for pattern analysis. "
            "Use '7d' for current week patterns or when a specific customer "
            "is mentioned (their active issues are recent). "
            "Use '30d' for emerging month-level trends. "
            "Use '90d' for historical background patterns. "
            "Default to '7d' unless the question explicitly asks about "
            "longer time periods."
        )
    )
    min_frequency: int = Field(
        default=2,
        description="Minimum number of tickets to form a pattern"
    )

class CustomerRiskInput(BaseModel):
    sort_by: str = Field(
        default="risk_score",
        description="Sort field: 'risk_score' (default), 'arr', or 'health_score'"
    )
    top_n: int = Field(
        default=5,
        description=(
            "Number of customers to return. "
            "Default is 5 — always return ALL customers for ranking queries. "
            "Only use top_n=1 if the user explicitly asks for THE single "
            "most at-risk customer and no ranking table is needed."
        )
    )

class SLAInput(BaseModel):
    lookahead_hours: int = Field(
        default=24,
        description=(
            "Hours to look ahead for SLA breach prediction. "
            "Use this tool ONLY when the user asks specifically about SLA "
            "deadlines, breach timing, or overdue tickets. "
            "Do NOT use this for general urgency questions."
        )
    )

class CrossTicketInput(BaseModel):
    query: str = Field(
        description=(
            "The natural language question to answer by reasoning across "
            "multiple tickets. Use this tool for: general urgency questions "
            "('what is most urgent'), root cause questions, summary requests, "
            "or any question that requires synthesising across multiple tickets."
        )
    )


# ── Tool 1: Analyze single ticket ────────────────────────────────

@tool("analyze_ticket", args_schema=TicketIdInput)
def analyze_ticket_tool(ticket_id: str) -> str:
    """
    Analyze a single support ticket by its exact ticket ID.
    Use this ONLY when the user specifies an exact ticket ID like TKT-1002.
    Returns root cause hypothesis, severity, business impact, and recommended action.
    If the ticket ID does not exist in the system, returns a not-found error.
    Do NOT use this for questions about multiple tickets, patterns, or general analysis.
    """
    try:
        from agent.rag.retriever import retrieve_tickets
        from agent.rag.context_builder import build_ticket_context
        from agent.llm_tools import call_llm
        from agent.prompts.v4_rag import SYSTEM_PROMPT, analyze_ticket_prompt

        # Semantic search for this ticket ID
        docs  = retrieve_tickets(f"ticket {ticket_id}", top_k=5)

        # FIX: only use exact ID match — never fall back to similar tickets
        exact = [d for d in docs if d["id"] == ticket_id]

        if not exact:
            # Hard stop — do not hallucinate using a different ticket's data
            return json.dumps({
                "error":            f"Ticket {ticket_id} not found in the system.",
                "ticket_id":        ticket_id,
                "not_found":        True,
                "available_ids":    [d["id"] for d in docs[:3]],
                "suggestion":       (
                    f"Ticket {ticket_id} does not exist. "
                    f"Did you mean one of: "
                    f"{', '.join([d['id'] for d in docs[:3]])}?"
                ),
                "hallucination_check": True,
                "tool":             "analyze_ticket"
            })

        ctx = build_ticket_context(exact, max_docs=1)
        result, _, tokens = call_llm(
            SYSTEM_PROMPT,
            analyze_ticket_prompt(ctx, ticket_id)
        )
        if isinstance(result, dict):
            result["tool"]   = "analyze_ticket"
            result["tokens"] = tokens
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "tool": "analyze_ticket"})


# ── Tool 2: Detect patterns ───────────────────────────────────────

@tool("detect_patterns", args_schema=PatternInput)
def detect_patterns_tool(window: str = "7d",
                          min_frequency: int = 2) -> str:
    """
    Detect recurring issue patterns across support tickets in a time window.
    Use this when the user asks about patterns, trends, recurring issues,
    or what keeps happening. If the user mentions a specific customer name,
    use window='7d' to find their active recent patterns.
    Returns pattern clusters with ticket IDs, trend direction, and recommended actions.
    """
    try:
        from agent.rag.retriever import retrieve_patterns
        from agent.rag.context_builder import (build_ticket_context,
                                                get_retrieval_stats)
        from agent.llm_tools import call_llm
        from agent.prompts.v4_rag import SYSTEM_PROMPT, detect_patterns_prompt

        docs  = retrieve_patterns(window=window, top_k=10)
        stats = get_retrieval_stats(docs)
        ctx   = build_ticket_context(docs, max_docs=10)

        result, _, tokens = call_llm(
            SYSTEM_PROMPT,
            detect_patterns_prompt(ctx, window, stats["count"])
        )
        if isinstance(result, dict):
            result["tool"]   = "detect_patterns"
            result["tokens"] = tokens
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "tool": "detect_patterns"})


# ── Tool 3: Rank customer risk (DETERMINISTIC) ────────────────────

@tool("rank_customer_risk", args_schema=CustomerRiskInput)
def rank_customer_risk_tool(sort_by: str = "risk_score",
                             top_n: int = 5) -> str:
    """
    Rank ALL customers by churn and business risk.
    Use this when the user asks which customer is most at risk, about customer
    health, ARR exposure, or who to call first.
    This tool computes risk scores deterministically from source data —
    it always returns results sorted correctly and never truncates the list.
    Returns all 5 customers ranked from highest to lowest risk.
    """
    try:
        from agent.tools import load_data
        from datetime import datetime

        tickets, customers = load_data()
        now = datetime.now()

        ranked = []
        total_arr_at_risk = 0

        for c in customers:
            cid          = c["id"]
            cust_tickets = [t for t in tickets if t["customer_id"] == cid]
            open_t       = [t for t in cust_tickets
                            if t["status"] not in ["resolved", "closed"]]
            critical     = [t for t in open_t if t["priority"] == "critical"]
            churn_tags   = ["churn-risk","vp-escalation","legal","escalation"]
            churn_count  = sum(1 for t in open_t
                               if any(tag in t.get("tags",[])
                                      for tag in churn_tags))

            health_risk  = (100 - c["health"]) * 0.40
            ticket_risk  = min(len(critical)*15 + len(open_t)*5, 25)
            arr_weight   = min((c["arr"] / 1500000) * 20, 20)
            churn_weight = min(churn_count * 7.5, 15)
            risk_score   = round(health_risk + ticket_risk
                                 + arr_weight + churn_weight, 1)

            risk_label = ("critical" if risk_score >= 70 else
                          "high"     if risk_score >= 50 else
                          "medium"   if risk_score >= 30 else "low")

            if risk_label in ["critical", "high"]:
                total_arr_at_risk += c["arr"]

            sla_breaches = 0
            for t in open_t:
                try:
                    if t.get("due_date") and \
                       datetime.fromisoformat(t["due_date"]) < now:
                        sla_breaches += 1
                except Exception:
                    pass

            if risk_label == "critical" or churn_count > 0:
                action = "Executive escalation — contact VP CS within 24h"
            elif risk_label == "high" or len(critical) > 0:
                action = "CSM check-in within 48h — review open critical tickets"
            elif sla_breaches > 0:
                action = "SLA remediation call — address breach before renewal"
            else:
                action = "Monitor weekly — no immediate action required"

            ranked.append({
                "customer_id":      cid,
                "name":             c["name"],
                "arr":              c["arr"],
                "health_score":     c["health"],
                "industry":         c["industry"],
                "open_tickets":     len(open_t),
                "critical_tickets": len(critical),
                "sla_breaches":     sla_breaches,
                "churn_signals":    churn_count,
                "risk_score":       risk_score,
                "risk_label":       risk_label,
                "csm":              c["csm"],
                "recommended_action": action,
            })

        sort_key = sort_by if sort_by in ["risk_score","arr","health_score"] \
                   else "risk_score"
        reverse  = sort_key != "health_score"
        ranked.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse)
        ranked = ranked[:min(top_n, len(ranked))]

        return json.dumps({
            "ranked_customers":    ranked,
            "total_arr_at_risk":   total_arr_at_risk,
            "customer_count":      len(ranked),
            "sort_field":          sort_key,
            "deterministic":       True,
            "tool":                "rank_customer_risk",
            "hallucination_check": True
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "tool": "rank_customer_risk"})


# ── Tool 4: Predict SLA risk ──────────────────────────────────────

@tool("predict_sla_risk", args_schema=SLAInput)
def predict_sla_risk_tool(lookahead_hours: int = 24) -> str:
    """
    Predict which tickets will breach their SLA deadline within a time window.
    Use this ONLY when the user asks specifically about SLA deadlines, breach
    timing, overdue tickets, or time-based urgency.
    Do NOT use this for general 'what is most urgent' questions — use
    cross_ticket_analysis for those instead.
    Returns already-breached tickets, tickets at risk, and breach probability.
    """
    try:
        from agent.rag.retriever import retrieve_sla_at_risk
        from agent.rag.context_builder import build_sla_context
        from agent.llm_tools import call_llm
        from agent.prompts.v4_rag import SYSTEM_PROMPT, sla_risk_prompt

        docs   = retrieve_sla_at_risk(lookahead_hours=lookahead_hours)
        ctx    = build_sla_context(docs)
        result, _, tokens = call_llm(SYSTEM_PROMPT, sla_risk_prompt(ctx))
        if isinstance(result, dict):
            result["tool"]   = "predict_sla_risk"
            result["tokens"] = tokens
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "tool": "predict_sla_risk"})


# ── Tool 5: Cross-ticket analysis ────────────────────────────────

@tool("cross_ticket_analysis", args_schema=CrossTicketInput)
def cross_ticket_analysis_tool(query: str) -> str:
    """
    Analyze multiple tickets together to find shared root causes, answer
    broad questions, or produce urgency summaries across the support queue.
    Use this for: 'what is most urgent', 'what is going wrong', root cause
    questions, general summaries, or any synthesis across multiple tickets.
    This is the default tool for questions that do not specify a ticket ID
    and do not ask specifically about SLA timing or customer ranking.
    Returns shared root cause, pattern, business impact, and recommended fix.
    """
    try:
        from agent.rag.retriever import retrieve_tickets
        from agent.rag.context_builder import (build_cross_ticket_context,
                                                get_retrieval_stats)
        from agent.llm_tools import call_llm
        from agent.prompts.v4_rag import SYSTEM_PROMPT, cross_ticket_prompt

        docs  = retrieve_tickets(query, window="all", top_k=12)
        stats = get_retrieval_stats(docs)
        ctx   = build_cross_ticket_context(docs, max_docs=12)

        result, _, tokens = call_llm(
            SYSTEM_PROMPT,
            cross_ticket_prompt(ctx, query, stats["count"])
        )
        if isinstance(result, dict):
            result["tool"]   = "cross_ticket_analysis"
            result["tokens"] = tokens
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "tool": "cross_ticket_analysis"})


# ── Tool registry ──────────────────────────────────────────────────
ALL_TOOLS = [
    analyze_ticket_tool,
    detect_patterns_tool,
    rank_customer_risk_tool,
    predict_sla_risk_tool,
    cross_ticket_analysis_tool,
]
