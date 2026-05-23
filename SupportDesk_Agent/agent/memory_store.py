"""
memory_store.py — Short-term and long-term memory for Phase 6

Short-term memory:
  ConversationBufferWindowMemory — keeps last K exchanges in RAM
  Resets when session ends or user types 'reset'
  Injected into every LLM call as conversation history

Long-term memory:
  JSON file store — persists across sessions
  Stores: escalation history, user preferences, resolved patterns,
          feedback signals, customer notes
  Read at session start, written after every interaction
"""

import json, os
from datetime import datetime
from langchain.memory import ConversationBufferWindowMemory

# ── Paths ─────────────────────────────────────────────────────────
PROJECT_ROOT    = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE     = os.path.join(
    os.path.dirname(PROJECT_ROOT), "data", "long_term_memory.json"
)

# ── Short-term memory config ──────────────────────────────────────
WINDOW_SIZE = 6   # remember last 6 exchanges (3 user + 3 assistant)


def create_short_term_memory() -> ConversationBufferWindowMemory:
    """
    Create a fresh short-term memory buffer for a new session.
    Keeps last WINDOW_SIZE messages — older messages are dropped.
    """
    return ConversationBufferWindowMemory(
        k=WINDOW_SIZE,
        memory_key="chat_history",
        return_messages=True,
        human_prefix="Support Lead",
        ai_prefix="Agent"
    )


# ── Long-term memory schema ───────────────────────────────────────
DEFAULT_LONG_TERM = {
    "escalations": [],          # [{ticket_id, customer, timestamp, resolved}]
    "resolved_patterns": [],    # [{pattern, root_cause, fix, timestamp}]
    "customer_notes": {},       # {customer_id: [note strings]}
    "user_preferences": {
        "default_window":    "7d",
        "preferred_sort":    "risk_score",
        "escalation_threshold": 70,
    },
    "session_count":  0,
    "last_session":   None,
    "feedback_log":   [],       # [{query, rating, note, timestamp}]
}


def load_long_term_memory() -> dict:
    """Load long-term memory from JSON file. Creates default if missing."""
    if not os.path.exists(MEMORY_FILE):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        save_long_term_memory(DEFAULT_LONG_TERM.copy())
        return DEFAULT_LONG_TERM.copy()
    try:
        with open(MEMORY_FILE) as f:
            data = json.load(f)
        # Merge with defaults to handle missing keys from older versions
        for key, val in DEFAULT_LONG_TERM.items():
            if key not in data:
                data[key] = val
        return data
    except (json.JSONDecodeError, IOError):
        return DEFAULT_LONG_TERM.copy()


def save_long_term_memory(memory: dict) -> None:
    """Persist long-term memory to JSON file."""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def log_escalation(memory: dict, ticket_id: str,
                   customer: str, resolved: bool = False) -> dict:
    """Record an escalation in long-term memory."""
    memory["escalations"].append({
        "ticket_id": ticket_id,
        "customer":  customer,
        "timestamp": datetime.now().isoformat(),
        "resolved":  resolved
    })
    save_long_term_memory(memory)
    return memory


def log_resolved_pattern(memory: dict, pattern: str,
                          root_cause: str, fix: str) -> dict:
    """Record a resolved pattern so it is not re-investigated next session."""
    memory["resolved_patterns"].append({
        "pattern":    pattern,
        "root_cause": root_cause,
        "fix":        fix,
        "timestamp":  datetime.now().isoformat()
    })
    save_long_term_memory(memory)
    return memory


def add_customer_note(memory: dict, customer_id: str, note: str) -> dict:
    """Append a note to a customer's memory record."""
    if customer_id not in memory["customer_notes"]:
        memory["customer_notes"][customer_id] = []
    memory["customer_notes"][customer_id].append(
        f"{datetime.now().strftime('%Y-%m-%d')}: {note}"
    )
    save_long_term_memory(memory)
    return memory


def log_feedback(memory: dict, query: str,
                 rating: int, note: str = "") -> dict:
    """
    Store feedback on a response (Phase 7 prep).
    rating: 1=poor, 2=fair, 3=good, 4=great, 5=excellent
    """
    memory["feedback_log"].append({
        "query":     query,
        "rating":    rating,
        "note":      note,
        "timestamp": datetime.now().isoformat()
    })
    save_long_term_memory(memory)
    return memory


def build_memory_context(memory: dict) -> str:
    """
    Build a concise context string injected into every system prompt.
    Tells the agent what it already knows from past sessions.
    """
    lines = []

    # Recent unresolved escalations
    unresolved = [e for e in memory["escalations"] if not e["resolved"]]
    if unresolved:
        recent = unresolved[-3:]  # last 3 only
        escalation_str = ", ".join(
            f"{e['ticket_id']} ({e['customer']})" for e in recent
        )
        lines.append(f"Unresolved escalations from prior sessions: {escalation_str}")

    # Known resolved patterns — avoid re-investigating
    if memory["resolved_patterns"]:
        recent_fix = memory["resolved_patterns"][-1]
        lines.append(
            f"Known resolved pattern: '{recent_fix['pattern']}' — "
            f"fix was: {recent_fix['fix']}"
        )

    # Customer notes
    if memory["customer_notes"]:
        for cid, notes in list(memory["customer_notes"].items())[-2:]:
            lines.append(f"Note on {cid}: {notes[-1]}")

    # User preferences
    prefs = memory.get("user_preferences", {})
    if prefs:
        lines.append(
            f"User preferences: default window={prefs.get('default_window','7d')}, "
            f"sort by={prefs.get('preferred_sort','risk_score')}"
        )

    if not lines:
        return "No prior session context available."

    return "MEMORY FROM PRIOR SESSIONS:\n" + "\n".join(f"- {l}" for l in lines)

# PHASE7 FEEDBACK ANALYSIS AND ADAPTATION

def get_feedback_summary(memory: dict) -> dict:
    """
    Analyse feedback log and return behaviour modifiers.

    Returns:
      avg_rating:        float — overall quality signal
      low_rated_intents: list  — tool types that got poor ratings
      high_rated_intents:list  — tool types that got good ratings
      depth_preference:  str   — "detailed" | "concise" | "neutral"
      common_complaints: list  — recurring words in low-rated notes
    """
    feedback = memory.get("feedback_log", [])
    if not feedback:
        return {
            "avg_rating":         None,
            "low_rated_intents":  [],
            "high_rated_intents": [],
            "depth_preference":   "neutral",
            "common_complaints":  [],
            "total_feedback":     0
        }

    ratings   = [f["rating"] for f in feedback]
    avg       = round(sum(ratings) / len(ratings), 2)
    low       = [f for f in feedback if f["rating"] <= 2]
    high      = [f for f in feedback if f["rating"] >= 4]

    # Extract complaint keywords from low-rated notes
    complaints = []
    for f in low:
        note = f.get("note", "").lower()
        for word in ["brief", "shallow", "missing", "wrong",
                     "incomplete", "vague", "generic"]:
            if word in note and word not in complaints:
                complaints.append(word)

    # Depth preference from notes
    depth = "neutral"
    all_notes = " ".join(f.get("note","") for f in feedback).lower()
    if "more detail" in all_notes or "too brief" in all_notes:
        depth = "detailed"
    elif "too long" in all_notes or "concise" in all_notes:
        depth = "concise"

    return {
        "avg_rating":         avg,
        "low_rated_intents":  [f.get("query","")[:50] for f in low],
        "high_rated_intents": [f.get("query","")[:50] for f in high],
        "depth_preference":   depth,
        "common_complaints":  complaints,
        "total_feedback":     len(feedback)
    }


def build_adaptive_context(memory: dict) -> str:
    """
    Build behaviour modifier string injected into system prompt.
    Translates feedback signals into concrete agent instructions.
    """
    summary = get_feedback_summary(memory)
    lines   = []

    if summary["avg_rating"] is None:
        return ""   # no feedback yet — no adaptation

    lines.append(
        f"FEEDBACK SUMMARY ({summary['total_feedback']} ratings, "
        f"avg: {summary['avg_rating']}/5):"
    )

    # Depth modifier
    if summary["depth_preference"] == "detailed":
        lines.append(
            "- User feedback indicates responses are too brief. "
            "Provide MORE detail: cite more ticket IDs, include more "
            "evidence quotes, explain the reasoning behind recommendations."
        )
    elif summary["depth_preference"] == "concise":
        lines.append(
            "- User feedback indicates responses are too long. "
            "Be MORE concise: lead with the key finding, "
            "limit evidence to 2 quotes, skip repetition."
        )

    # Complaint-specific adaptations
    if "shallow" in summary["common_complaints"] or \
       "generic" in summary["common_complaints"]:
        lines.append(
            "- Prior responses flagged as too generic. "
            "Always cite specific ticket IDs and exact dollar figures. "
            "Never use vague language like 'several tickets' or 'some customers'."
        )

    if "missing" in summary["common_complaints"]:
        lines.append(
            "- Prior responses flagged as missing information. "
            "When calling detect_patterns, always follow up with "
            "cross_ticket_analysis for root cause depth."
        )

    if "wrong" in summary["common_complaints"]:
        lines.append(
            "- Prior responses flagged as incorrect. "
            "Double-check all ticket IDs and ARR figures before responding. "
            "If uncertain, state confidence level explicitly."
        )

    # High performance positive reinforcement
    if summary["avg_rating"] >= 4:
        lines.append(
            "- Recent responses have been well-rated. "
            "Maintain current depth and specificity."
        )

    return "\n".join(lines) if len(lines) > 1 else ""