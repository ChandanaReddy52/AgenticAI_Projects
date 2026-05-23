"""
context_builder.py — Assemble retrieved documents into prompt context
Location: supportdesk_agent/agent/rag/context_builder.py

Converts retrieval results into clean, token-efficient prompt text.
Each function targets a specific tool's context needs.
"""


def build_ticket_context(docs: list, max_docs: int = 8) -> str:
    """Convert retrieved ticket docs into prompt-injectable text."""
    if not docs:
        return "No relevant tickets found in the specified context."

    lines = [f"RETRIEVED TICKETS ({min(len(docs), max_docs)} most relevant):\n"]
    for doc in docs[:max_docs]:
        meta = doc.get("metadata", {})
        rel  = doc.get("relevance", 0)
        lines.append(
            f"[Relevance: {rel:.3f}] {meta.get('ticket_id','?')} "
            f"[{meta.get('priority','?').upper()}] [{meta.get('status','?')}]\n"
            f"{doc['document']}\n"
            f"{'─'*40}"
        )
    return "\n".join(lines)


def build_customer_context(docs: list) -> str:
    """
    Convert ALL customer docs into numbered, prompt-injectable text.
    Explicit numbering fixes Q3 Phase 3 failure (LLM truncated the list).
    """
    if not docs:
        return "No customer data available."

    total = len(docs)
    lines = [
        f"ALL CUSTOMERS RANKED BY RISK SCORE "
        f"({total} total — include ALL {total} in your response):\n"
    ]
    for i, doc in enumerate(docs, 1):
        lines.append(
            f"CUSTOMER {i} of {total}:\n"
            f"{doc['document']}\n"
            f"{'─'*40}"
        )
    return "\n".join(lines)


def build_sla_context(docs: list) -> str:
    """Convert SLA-at-risk ticket docs into prompt context."""
    if not docs:
        return "No SLA risks detected in the current dataset."

    breached = [d for d in docs if d["metadata"].get("is_breached")]
    at_risk  = [d for d in docs if not d["metadata"].get("is_breached")]

    lines = []
    if breached:
        lines.append(f"⛔ ALREADY BREACHED ({len(breached)} tickets):")
        for d in breached:
            meta = d["metadata"]
            lines.append(
                f"  {meta.get('ticket_id','?')} | "
                f"{meta.get('customer_name','?')} | "
                f"ARR: ${meta.get('arr',0):,.0f} | "
                f"{meta.get('priority','?').upper()}\n"
                f"  {d['document'][:200]}\n"
            )

    if at_risk:
        lines.append(f"\n🔴 AT RISK — next 24h ({len(at_risk)} tickets):")
        for d in at_risk:
            meta  = d["metadata"]
            hours = meta.get("hours_until_breach", "?")
            prob  = meta.get("breach_probability", "?")
            lines.append(
                f"  {meta.get('ticket_id','?')} | {hours}h remaining | "
                f"prob {prob} | {meta.get('customer_name','?')} | "
                f"ARR: ${meta.get('arr',0):,.0f}\n"
                f"  {d['document'][:200]}\n"
            )

    return "\n".join(lines)


def build_cross_ticket_context(docs: list, max_docs: int = 12) -> str:
    """
    Context for cross-ticket analysis — more docs, full descriptions.
    Explicit instruction to cite ALL relevant tickets.
    Fixes Q5 Phase 3 failure where only 2 tickets were cited.
    """
    if not docs:
        return "No relevant tickets found."

    total = min(len(docs), max_docs)
    lines = [
        f"ALL RELEVANT TICKETS FOR CROSS-TICKET ANALYSIS "
        f"({total} tickets — cite ALL relevant ones in your response):\n"
    ]
    for doc in docs[:max_docs]:
        meta = doc.get("metadata", {})
        lines.append(
            f"{meta.get('ticket_id','?')} "
            f"[{meta.get('priority','?').upper()}] "
            f"[{meta.get('status','?')}] — "
            f"{meta.get('customer_name','?')}\n"
            f"{doc['document']}\n"
            f"{'─'*40}"
        )
    return "\n".join(lines)


def get_retrieval_stats(docs: list) -> dict:
    """Summary statistics for logging and evaluation."""
    if not docs:
        return {"count": 0, "avg_relevance": 0.0,
                "min_relevance": 0.0, "max_relevance": 0.0,
                "ticket_ids": []}

    relevances = [d.get("relevance", 0) for d in docs]
    return {
        "count":         len(docs),
        "avg_relevance": round(sum(relevances) / len(relevances), 4),
        "min_relevance": round(min(relevances), 4),
        "max_relevance": round(max(relevances), 4),
        "ticket_ids":    [d["id"] for d in docs],
    }
