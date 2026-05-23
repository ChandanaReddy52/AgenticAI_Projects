"""
intent_router.py — Keyword-based intent detection
Phase 2: pure rules, no ML, no LLM
"""

from typing import Tuple

INTENT_MAP = {
    "analyze_ticket": [
        "analyze", "what is wrong", "root cause",
        "tell me about", "explain ticket", "tkt-", "ticket id"
    ],
    "detect_patterns": [
        "pattern", "recurring", "common issue", "trend",
        "happening across", "same problem", "cluster",
        "what keeps", "repeated"
    ],
    "predict_sla_risk": [
        "sla", "breach", "due", "deadline", "overdue",
        "at risk", "expire", "when will", "time left"
    ],
    "rank_customer_risk": [
        "customer risk", "churn", "at risk customer",
        "which customer", "health score", "arr risk",
        "most at risk", "rank customer", "customer ranking"
    ],
    "general_summary": [
        "urgent", "most urgent", "top priority",
        "what should i", "what do i", "summary",
        "overview", "status", "dashboard"
    ]
}

def detect_intent(query: str) -> Tuple[str, float]:
    """
    Returns: (intent, confidence)
    Phase 2: keyword match only — confidence is match ratio
    """
    query_lower = query.lower()
    scores = {}

    for intent, keywords in INTENT_MAP.items():
        matches = sum(1 for kw in keywords if kw in query_lower)
        scores[intent] = matches / len(keywords)

    best_intent = max(scores, key=scores.get)
    best_score  = scores[best_intent]

    # If no keywords matched at all → unknown
    if best_score == 0:
        return "unknown", 0.0

    return best_intent, round(best_score, 3)