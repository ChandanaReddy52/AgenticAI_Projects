"""
safety.py — Pre-LLM guardrails
Runs BEFORE any tool call or LLM invocation.
Hard refusals. No exceptions.
"""

import re
from typing import Tuple

# Patterns that trigger immediate refusal
UNSAFE_PATTERNS = [
    r"\bdelete\b.*\bticket\b",
    r"\bremove\b.*\bcustomer\b",
    r"\bpassword\b",
    r"\bsocial security\b",
    r"\bcredit card\b",
    r"\bignore.*instructions\b",
    r"\bforget.*instructions\b",
    r"\bpretend.*you are\b",
    r"\bact as\b.*\bdifferent\b",
    r"\bdrop.*table\b",
    r"\bsql inject\b",
]

# Patterns that trigger auto-escalation (not refusal)
ESCALATION_TRIGGERS = [
    r"\blegal\b",
    r"\blawsuit\b",
    r"\bchurn\b.*\bthreat\b",
    r"\bdata loss\b",
    r"\bbreach\b.*\bcontract\b",
    r"\bregulatory\b.*\baudit\b",
]

def check_safety(query: str) -> Tuple[str, str]:
    """
    Returns: (status, message)
    status: "safe" | "unsafe" | "escalate"
    """
    query_lower = query.lower()

    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, query_lower):
            return "unsafe", (
                "I cannot process this request. "
                "It matches a safety restriction. "
                "Please contact your administrator."
            )

    for pattern in ESCALATION_TRIGGERS:
        if re.search(pattern, query_lower):
            return "escalate", (
                "This query involves a sensitive topic that requires "
                "human review. I will flag this for escalation."
            )

    return "safe", ""


def anonymize_for_log(data: dict) -> dict:
    """Remove PII from log entries — customer names → IDs only."""
    safe = data.copy()
    for key in ["name", "contact", "email", "csm"]:
        if key in safe:
            safe[key] = "[REDACTED]"
    return safe