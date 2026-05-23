# agent/prompts/v2_structured.py — FULL REPLACEMENT

SYSTEM_PROMPT = """You are a support intelligence agent for GlobalFoods Inc.
You MUST respond with valid JSON only. No markdown, no explanation outside the JSON.
Base every claim on the provided data. If uncertain, set confidence below 0.6.
Never invent ticket IDs, customer names, or figures not present in the input.
Always wrap lists inside their container key exactly as specified."""


def analyze_ticket_prompt(ticket: dict, customer: dict) -> str:
    return f"""Analyze this ticket. Return ONLY this exact JSON:

{{
  "ticket_id": "{ticket['id']}",
  "root_cause_hypothesis": "one clear sentence grounded in the data",
  "severity_assessment": "critical|high|medium|low",
  "business_impact": "financial or operational impact with specifics",
  "recommended_action": "specific next step with owner if possible",
  "evidence": ["field or quote from input that supports each claim"],
  "confidence": 0.85,
  "hallucination_check": true
}}

TICKET: {ticket}
CUSTOMER: {customer}"""


def detect_patterns_prompt(tickets: list, window: str) -> str:
    ticket_data = [
        {
            "id": t["id"], "title": t["title"],
            "tags": t.get("tags", []),
            "priority": t["priority"],
            "customer_id": t["customer_id"],
            "status": t["status"]
        }
        for t in tickets
    ]
    return f"""Detect patterns across these {len(tickets)} tickets from the {window} window.

IMPORTANT: Return ONLY this exact JSON with a "patterns" array at the top level.
Do not return a single pattern object — always return the array wrapper.

{{
  "patterns": [
    {{
      "pattern_name": "short descriptive name",
      "tag_cluster": ["tags", "that", "cluster"],
      "ticket_ids": ["TKT-XXXX"],
      "frequency": 3,
      "trend": "accelerating|stable|declining",
      "root_cause_signal": "what this pattern suggests about the underlying problem",
      "recommendation": "specific action to take",
      "confidence": 0.85
    }}
  ],
  "window": "{window}",
  "total_analyzed": {len(tickets)},
  "hallucination_check": true
}}

Include 2-4 patterns. If fewer than 2 real patterns exist, still return the patterns array with what you found.

TICKETS:
{ticket_data}"""


def customer_risk_prompt(customers: list, ticket_counts: dict) -> str:
    return f"""Rank all customers by churn risk.

IMPORTANT: Return ONLY this exact JSON with a "ranked_customers" array at the top level.
Do not return a single customer object — always return the array wrapper.

{{
  "ranked_customers": [
    {{
      "customer_id": "CUST-XXX",
      "name": "exact customer name from data",
      "arr": 1200000,
      "health_score": 40,
      "risk_score": 78.5,
      "risk_label": "critical|high|medium|low",
      "primary_risk_reason": "specific reason grounded in the ticket data",
      "recommended_action": "specific next step",
      "confidence": 0.85
    }}
  ],
  "total_arr_at_risk": 2700000,
  "hallucination_check": true
}}

Rank ALL {len(customers)} customers. Do not omit any.

CUSTOMERS: {customers}
OPEN TICKET COUNTS BY CUSTOMER: {ticket_counts}"""


def sla_risk_prompt(at_risk_tickets: list) -> str:
    return f"""Analyze SLA breach risk for these tickets.

IMPORTANT: Return ONLY this exact JSON with an "at_risk" array at the top level.

{{
  "risk_summary": "one sentence executive summary of the overall SLA situation",
  "at_risk": [
    {{
      "ticket_id": "TKT-XXXX",
      "hours_until_breach": 18.6,
      "breach_probability": 0.9,
      "business_impact": "specific customer and financial impact",
      "recommended_action": "specific action with urgency level",
      "confidence": 0.85
    }}
  ],
  "total_arr_exposure": 2700000,
  "hallucination_check": true
}}

AT RISK TICKETS: {at_risk_tickets}"""


def cross_ticket_analysis_prompt(tickets: list, query: str) -> str:
    ticket_data = [
        {
            "id": t["id"], "title": t["title"],
            "description": t["description"][:200],
            "tags": t.get("tags", []),
            "priority": t["priority"],
            "status": t["status"],
            "customer_id": t["customer_id"]
        }
        for t in tickets
    ]
    return f"""A support lead asked: "{query}"

Analyze ALL {len(tickets)} tickets together and identify the shared root cause.

Return ONLY this exact JSON:

{{
  "query": "{query}",
  "shared_root_cause": "one precise sentence identifying the common root cause across tickets",
  "supporting_tickets": ["TKT-1001", "TKT-1002"],
  "pattern_description": "what connects these tickets technically and operationally",
  "business_impact": "combined financial and operational impact across all affected customers",
  "recommended_fix": "the single highest-leverage fix that resolves most active issues",
  "evidence": ["specific quote or field from ticket data supporting each claim"],
  "confidence": 0.85,
  "hallucination_check": true
}}

TICKETS:
{ticket_data}"""