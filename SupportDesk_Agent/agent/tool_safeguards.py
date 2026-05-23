"""
tool_safeguards.py — Guardrails and loop prevention for Phase 5
Location: supportdesk_agent/agent/tool_safeguards.py

Three layers of protection:
  1. Pre-execution guardrails — block unsafe tool inputs
  2. Tool call counter — prevent infinite loops
  3. Output validator — catch hallucinated tool names
"""

import re
from typing import Any


# ── 1. Pre-execution guardrails ───────────────────────────────────

UNSAFE_TOOL_INPUTS = [
    r"\bdelete\b",
    r"\bdrop\b.*\btable\b",
    r"\btruncate\b",
    r"\bpassword\b",
    r"\bapi.?key\b",
    r"\bsecret\b",
    r"\bignore.*instructions\b",
    r"\bprompt.?inject\b",
]

VALID_TOOL_NAMES = {
    "analyze_ticket",
    "detect_patterns",
    "rank_customer_risk",
    "predict_sla_risk",
    "cross_ticket_analysis",
}


def check_tool_input(tool_name: str, tool_input: Any) -> tuple[bool, str]:
    """
    Validate tool name and input before execution.
    Returns (is_safe, reason).
    """
    # Validate tool name
    if tool_name not in VALID_TOOL_NAMES:
        return False, (
            f"Invalid tool name '{tool_name}'. "
            f"Valid tools: {', '.join(sorted(VALID_TOOL_NAMES))}"
        )

    # Check input for unsafe patterns
    input_str = str(tool_input).lower()
    for pattern in UNSAFE_TOOL_INPUTS:
        if re.search(pattern, input_str):
            return False, (
                f"Tool input contains unsafe pattern: '{pattern}'. "
                f"Request blocked."
            )

    return True, ""


# ── 2. Loop prevention ────────────────────────────────────────────

class ToolCallTracker:
    """
    Tracks tool calls per session to prevent infinite loops.

    Limits:
      MAX_CALLS_TOTAL: max tool calls in one agent turn
      MAX_CALLS_PER_TOOL: max times the same tool can be called
    """

    MAX_CALLS_TOTAL    = 5
    MAX_CALLS_PER_TOOL = 2

    def __init__(self):
        self.reset()

    def reset(self):
        self._total    = 0
        self._per_tool = {}

    def record(self, tool_name: str) -> tuple[bool, str]:
        """
        Record a tool call. Returns (allowed, reason).
        Call this BEFORE executing the tool.
        """
        self._total += 1
        self._per_tool[tool_name] = self._per_tool.get(tool_name, 0) + 1

        if self._total > self.MAX_CALLS_TOTAL:
            return False, (
                f"Loop prevention: {self._total} tool calls exceeded "
                f"max of {self.MAX_CALLS_TOTAL} per turn. "
                f"Returning partial result."
            )

        if self._per_tool[tool_name] > self.MAX_CALLS_PER_TOOL:
            return False, (
                f"Loop prevention: '{tool_name}' called "
                f"{self._per_tool[tool_name]} times, "
                f"max is {self.MAX_CALLS_PER_TOOL}. "
                f"Stopping to prevent loop."
            )

        return True, ""

    def summary(self) -> dict:
        return {
            "total_calls": self._total,
            "per_tool":    self._per_tool
        }


# ── 3. Output validator ───────────────────────────────────────────

def validate_tool_output(tool_name: str, output: str) -> tuple[bool, str]:
    """
    Validate tool output before passing back to agent.
    Returns (is_valid, cleaned_output).
    """
    import json

    # Must be valid JSON
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return False, json.dumps({
            "error":  "Tool returned invalid JSON",
            "tool":   tool_name,
            "raw":    output[:200]
        })

    # Must not contain error key with critical failures
    if "error" in parsed:
        error_msg = str(parsed["error"])
        # Allow non-critical errors through
        if any(word in error_msg.lower()
               for word in ["not found", "no tickets", "no customers"]):
            return True, output
        # Block critical errors
        return False, json.dumps({
            "error":  f"Tool '{tool_name}' failed: {error_msg}",
            "tool":   tool_name
        })

    return True, output