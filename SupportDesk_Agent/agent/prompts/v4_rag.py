"""
v4_rag.py — RAG-aware prompt templates
Location: supportdesk_agent/agent/prompts/v4_rag.py

Fixes applied vs original:
  1. confidence placeholder changed from 0.0 to descriptive instruction
     so LLM computes confidence rather than copying the literal 0.0
  2. customer_risk_prompt: stronger enforcement to return ALL customers
     and explicit numbered format to prevent LLM truncation (fixes Q3)
  3. cross_ticket_prompt: explicit instruction not to sum ARR across
     tickets — use unique customer ARR only (fixes Q5 ARR hallucination)
  4. All prompts: clearer array wrapper enforcement
"""

SYSTEM_PROMPT = """You are a support intelligence agent for GlobalFoods Inc.
You have been given RETRIEVED context from a vector database.
Base ALL claims strictly on the retrieved context provided.
If a fact is not in the retrieved context, state "not available in retrieved context."
Return ONLY valid JSON. No markdown. No explanation outside the JSON.
Always return complete arrays — never omit or truncate list items.
Set confidence to your genuine assessment (0.0=uncertain, 1.0=very confident).
Do NOT copy confidence values from the template — compute them from evidence quality."""


def analyze_ticket_prompt(ticket_context: str, ticket_id: str) -> str:
    return f"""Analyze ticket {ticket_id} using ONLY the retrieved context below.

Return ONLY this JSON:
{{
  "ticket_id": "{ticket_id}",
  "root_cause_hypothesis": "one precise sentence grounded in retrieved data",
  "severity_assessment": "critical|high|medium|low",
  "business_impact": "specific financial or operational impact with numbers from the data",
  "recommended_action": "specific next step with owner",
  "evidence": ["exact quote or field name from retrieved context supporting each claim"],
  "retrieval_grounded": true,
  "confidence": "<your assessment: 0.7 if you have clear evidence, 0.4 if partial, 0.2 if weak>",
  "hallucination_check": true
}}

RETRIEVED CONTEXT:
{ticket_context}"""


def detect_patterns_prompt(ticket_context: str, window: str,
                           ticket_count: int) -> str:
    return f"""Detect recurring patterns across these {ticket_count} retrieved tickets
from the {window} time window.

Return ONLY this JSON with a "patterns" array at the top level:
{{
  "patterns": [
    {{
      "pattern_name": "short descriptive name",
      "tag_cluster": ["tag1", "tag2"],
      "ticket_ids": ["TKT-XXXX", "TKT-YYYY"],
      "frequency": 3,
      "trend": "accelerating|stable|declining",
      "root_cause_signal": "what this pattern signals about the underlying problem",
      "recommendation": "specific action to take",
      "confidence": "<0.0-1.0 based on how clear the pattern is>"
    }}
  ],
  "window": "{window}",
  "total_analyzed": {ticket_count},
  "retrieval_grounded": true,
  "hallucination_check": true
}}

Return 2-4 patterns. Only cite ticket IDs that appear in the retrieved context below.

RETRIEVED TICKETS ({ticket_count} tickets):
{ticket_context}"""


def customer_risk_prompt(customer_context: str, customer_count: int) -> str:
    return f"""Rank ALL {customer_count} customers by churn risk using the retrieved data.

CRITICAL RULES:
1. You MUST return exactly {customer_count} entries in ranked_customers.
2. Do NOT omit any customer — even if they appear low risk.
3. Each entry must have a unique customer_id from the retrieved data.
4. Rank from HIGHEST risk (index 0) to LOWEST risk (last index).
5. Use the risk_score from the retrieved data to determine rank order.

Return ONLY this JSON:
{{
  "ranked_customers": [
    {{
      "customer_id": "CUST-XXX",
      "name": "exact name from retrieved data",
      "arr": 0,
      "health_score": 0,
      "risk_score": 0.0,
      "risk_label": "critical|high|medium|low",
      "primary_risk_reason": "specific reason from retrieved data",
      "recommended_action": "specific next step",
      "confidence": "<0.0-1.0 based on data completeness>"
    }}
  ],
  "total_arr_at_risk": "<sum of ARR for critical and high risk customers only>",
  "customer_count_returned": {customer_count},
  "retrieval_grounded": true,
  "hallucination_check": true
}}

The ranked_customers array MUST have exactly {customer_count} objects.
Verify your response includes all {customer_count} customers before returning.

RETRIEVED CUSTOMER DATA (ALL {customer_count} customers — include every one):
{customer_context}"""


def sla_risk_prompt(sla_context: str) -> str:
    return f"""Analyze SLA breach risk using ONLY the retrieved ticket data below.

Return ONLY this JSON:
{{
  "risk_summary": "one executive sentence summarising breach situation with ticket counts",
  "at_risk": [
    {{
      "ticket_id": "TKT-XXXX",
      "hours_until_breach": 0.0,
      "breach_probability": 0.0,
      "business_impact": "specific customer name and their ARR at risk",
      "recommended_action": "specific action with urgency level",
      "confidence": "<0.0-1.0>"
    }}
  ],
  "already_breached_count": 0,
  "total_arr_exposure": "<total ARR of unique affected customers — do not double-count>",
  "retrieval_grounded": true,
  "hallucination_check": true
}}

Only include tickets that appear in the retrieved context below.

RETRIEVED SLA DATA:
{sla_context}"""


def cross_ticket_prompt(ticket_context: str, query: str,
                        ticket_count: int) -> str:
    return f"""A support lead asked: "{query}"

Analyze ALL {ticket_count} retrieved tickets to answer this question.

CRITICAL RULES:
1. Cite as many relevant ticket IDs as possible in supporting_tickets.
2. For business_impact: identify UNIQUE customers affected and their ARR.
   Do NOT sum the same customer's ARR multiple times across different tickets.
   If GlobalFoods ($1.2M) appears in 5 tickets, count $1.2M only ONCE.
3. Base all claims on the retrieved ticket data only.

Return ONLY this JSON:
{{
  "query": "{query}",
  "shared_root_cause": "precise technical root cause in one sentence",
  "supporting_tickets": ["TKT-XXXX", "TKT-YYYY"],
  "pattern_description": "what technically connects these tickets",
  "business_impact": "unique customers affected: [name ($ARR), name ($ARR)] — total: $X",
  "recommended_fix": "single highest-leverage fix that resolves most active issues",
  "evidence": ["specific quote from ticket description supporting root cause"],
  "tickets_analyzed": {ticket_count},
  "retrieval_grounded": true,
  "confidence": "<0.0-1.0 based on evidence strength>",
  "hallucination_check": true
}}

RETRIEVED TICKETS ({ticket_count} tickets — cite ALL relevant ones):
{ticket_context}"""
