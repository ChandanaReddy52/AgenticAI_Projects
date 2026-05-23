"""
V3 — Chain-of-thought prompting.
Forces visible reasoning steps before conclusion.
Best for complex multi-ticket analysis.
Higher latency but higher reasoning quality.
"""

SYSTEM_PROMPT = """You are a senior support intelligence analyst for GlobalFoods Inc.
Think step by step before reaching conclusions.
Ground every claim in the provided data.
Format: REASONING section first, then ANSWER in JSON."""


def analyze_ticket_prompt(ticket: dict, customer: dict) -> str:
    return f"""Analyze this support ticket step by step.

Step 1: Read the title and description. What is literally happening?
Step 2: Look at the tags. What do they tell you about the failure category?
Step 3: Consider the customer ARR and health score. What is the business urgency?
Step 4: Based on steps 1-3, what is the most likely root cause?
Step 5: What is the single most important action to take first?

After your reasoning, output this JSON:
{{
  "ticket_id": "{ticket['id']}",
  "root_cause_hypothesis": "...",
  "severity_assessment": "critical|high|medium|low",
  "business_impact": "...",
  "recommended_action": "...",
  "evidence": ["..."],
  "confidence": 0.0,
  "hallucination_check": true
}}

TICKET: {ticket}
CUSTOMER: {customer}"""


def detect_patterns_prompt(tickets: list, window: str) -> str:
    ticket_data = [
        {"id": t["id"], "title": t["title"],
         "tags": t.get("tags",[]), "priority": t["priority"],
         "customer_id": t["customer_id"], "status": t["status"]}
        for t in tickets
    ]
    return f"""Find patterns across these {window} tickets using step-by-step reasoning.

Step 1: Group tickets by shared tags. List each group.
Step 2: For each group — how many tickets? Which customers? What priority distribution?
Step 3: Which groups are accelerating vs stable?
Step 4: For the top 3 groups — what does the pattern signal about the underlying problem?
Step 5: What is the highest-leverage recommendation for each?

Then output JSON:
{{
  "patterns": [
    {{
      "pattern_name": "...",
      "tag_cluster": ["..."],
      "ticket_ids": ["TKT-XXXX"],
      "frequency": 0,
      "trend": "accelerating|stable|declining",
      "root_cause_signal": "...",
      "recommendation": "...",
      "confidence": 0.0
    }}
  ],
  "window": "{window}",
  "total_analyzed": {len(tickets)},
  "hallucination_check": true
}}

TICKETS: {ticket_data}"""


def cross_ticket_analysis_prompt(tickets: list, query: str) -> str:
    """Chain-of-thought version of cross-ticket reasoning."""
    ticket_data = [
        {"id": t["id"], "title": t["title"],
         "description": t["description"][:200],
         "tags": t.get("tags",[]), "priority": t["priority"]}
        for t in tickets
    ]
    return f"""A support lead asked: "{query}"

Reason through this step by step:
Step 1: Which tickets are most relevant to this question? Why?
Step 2: What do the descriptions tell you when read together?
Step 3: What single root cause best explains the pattern across tickets?
Step 4: What is the combined business impact?
Step 5: What is the one fix that would have the most leverage?

Then output JSON:
{{
  "query": "{query}",
  "shared_root_cause": "...",
  "supporting_tickets": ["TKT-XXXX"],
  "pattern_description": "...",
  "business_impact": "...",
  "recommended_fix": "...",
  "evidence": ["..."],
  "confidence": 0.0,
  "hallucination_check": true
}}

TICKETS: {ticket_data}"""