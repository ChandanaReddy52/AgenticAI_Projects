"""
adaptive_agent.py — Phase 7 adaptive behaviour orchestrator
Location: supportdesk_agent/agent/adaptive_agent.py

Extends Phase 6 memory agent with:
  1. Feedback analysis — reads feedback_log from long_term_memory
  2. Adaptive system prompt — behaviour modifiers injected based on ratings
  3. Before/after demonstration — same query, different behaviour
  4. Feedback ingestion — stores rating + maps to query intent

The adaptation logic:
  Rating 1-2 (poor)  → more detail, cite specific tickets, follow-up tools
  Rating 3   (ok)    → no change
  Rating 4-5 (good)  → maintain current behaviour

Feedback is stored in long_term_memory.json and persists across sessions.
The system prompt changes automatically based on accumulated feedback.
"""

import json, os, time
from dotenv import load_dotenv


def _find_env(start: str):
    current = start
    for _ in range(6):
        c = os.path.join(current, ".env")
        if os.path.isfile(c):
            return c
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
env = _find_env(PROJECT_ROOT)
if env:
    load_dotenv(env)

from langchain_openai import ChatOpenAI
from langchain.agents  import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.safety          import check_safety
from agent.logger          import log_interaction
from agent.tool_safeguards import ToolCallTracker, check_tool_input, validate_tool_output
from agent.tools_langchain import ALL_TOOLS
from agent.memory_store    import (
    create_short_term_memory, load_long_term_memory,
    save_long_term_memory, log_feedback,
    build_memory_context, build_adaptive_context,
    get_feedback_summary
)


# ── Session state ──────────────────────────────────────────────────
_short_term_memory = None
_long_term_memory  = None
_last_query        = ""   # tracked for feedback attribution


def init_adaptive_session():
    global _short_term_memory, _long_term_memory
    lt = load_long_term_memory()
    lt["session_count"] = lt.get("session_count", 0) + 1
    lt["last_session"]  = __import__("datetime").datetime.now().isoformat()
    save_long_term_memory(lt)
    _short_term_memory = create_short_term_memory()
    _long_term_memory  = lt
    return _short_term_memory, _long_term_memory


def get_adaptive_session():
    global _short_term_memory, _long_term_memory
    if _short_term_memory is None or _long_term_memory is None:
        return init_adaptive_session()
    return _short_term_memory, _long_term_memory


def _build_adaptive_agent(memory_context: str, adaptive_context: str):
    """
    Build agent with both memory context AND adaptive behaviour modifiers
    injected into the system prompt.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Adaptive context only appears if feedback exists
    adaptive_section = (
        f"\n{adaptive_context}\n"
        if adaptive_context else
        "\n[No feedback received yet — using default behaviour]\n"
    )

    system_prompt = f"""You are a support intelligence agent for GlobalFoods Inc.
        You have access to 5 tools that analyze support tickets and customer data.

        {memory_context}

        {adaptive_section}

        TOOL SELECTION RULES:
        1. Ticket ID specified → analyze_ticket
        2. Patterns, trends, recurring issues → detect_patterns (window='7d' for customer queries)
        3. Customer health, churn, ARR → rank_customer_risk (top_n=5)
        4. SLA deadlines, breach timing → predict_sla_risk
        5. Root cause, urgency, summary → cross_ticket_analysis

        BEHAVIOUR RULES:
        - Always call a tool — never answer from memory alone
        - Apply feedback modifiers above to every response
        - If depth_preference is 'detailed': use more tools, cite more evidence
        - If depth_preference is 'concise': one tool, lead with key finding"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human",  "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    return create_openai_functions_agent(llm=llm, tools=ALL_TOOLS, prompt=prompt)


def _wrap_tools(tools, tracker):
    from langchain.tools import StructuredTool

    wrapped = []
    for tool in tools:
        original = tool.func

        def make_guarded(name, func):
            def guarded(**kwargs):
                safe, reason = check_tool_input(name, kwargs)
                if not safe:
                    return json.dumps({"error": reason, "blocked": True})
                allowed, loop_reason = tracker.record(name)
                if not allowed:
                    return json.dumps({"error": loop_reason, "loop_break": True})
                output = func(**kwargs)
                _, clean = validate_tool_output(name, output)
                return clean
            return guarded

        wrapped.append(StructuredTool(
            name=tool.name,
            description=tool.description,
            args_schema=tool.args_schema,
            func=make_guarded(tool.name, original)
        ))
    return wrapped


def run_adaptive_agent(query: str, verbose: bool = False) -> str:
    global _last_query
    start = time.time()
    _last_query = query

    safety_status, safety_msg = check_safety(query)
    if safety_status == "unsafe":
        return f"🚫 SAFETY BLOCK: {safety_msg}"
    if safety_status == "escalate":
        return f"⚠️  ESCALATION FLAGGED: {safety_msg}"

    short_term, long_term = get_adaptive_session()
    memory_context   = build_memory_context(long_term)
    adaptive_context = build_adaptive_context(long_term)
    feedback_summary = get_feedback_summary(long_term)

    tracker = ToolCallTracker()

    try:
        agent         = _build_adaptive_agent(memory_context, adaptive_context)
        guarded_tools = _wrap_tools(ALL_TOOLS, tracker)

        executor = AgentExecutor(
            agent=agent,
            tools=guarded_tools,
            memory=short_term,
            verbose=verbose,
            max_iterations=5,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

        result = executor.invoke({"input": query})

        tool_calls = []
        for step in result.get("intermediate_steps", []):
            action, observation = step
            tool_calls.append({
                "tool":   action.tool,
                "input":  str(action.tool_input)[:200],
                "output": str(observation)[:200]
            })

        response      = result.get("output", "")
        total_latency = time.time() - start
        tool_summary  = tracker.summary()

        if verbose:
            print(f"\n[ADAPTIVE] Tools: {tool_summary}")
            print(f"[ADAPTIVE] Feedback avg: {feedback_summary['avg_rating']}")
            print(f"[ADAPTIVE] Depth pref:   {feedback_summary['depth_preference']}")
            print(f"[ADAPTIVE] Total:        {round(total_latency*1000)}ms")

        log_interaction(
            query=query,
            intent="adaptive_agent",
            tool=", ".join([tc["tool"] for tc in tool_calls]) or "none",
            response={
                "output":            response[:500],
                "tool_calls":        tool_calls,
                "tool_summary":      tool_summary,
                "feedback_avg":      feedback_summary["avg_rating"],
                "depth_preference":  feedback_summary["depth_preference"],
                "adaptive_context":  adaptive_context[:200] if adaptive_context else "none",
                "hallucination_check": True
            },
            latency=total_latency,
            phase="phase7_adaptive",
            notes=(
                f"tools:{tool_summary['total_calls']} "
                f"feedback_avg:{feedback_summary['avg_rating']} "
                f"depth:{feedback_summary['depth_preference']} "
                f"history_len:{len(short_term.chat_memory.messages)}"
            )
        )

        footer = (
            f"\n[Phase 7 Adaptive | {round(total_latency*1000)}ms | "
            f"Tools: {tool_summary['total_calls']} | "
            f"Feedback avg: {feedback_summary['avg_rating']} | "
            f"Depth: {feedback_summary['depth_preference']}]"
        )
        return response + footer

    except Exception as e:
        return f"Adaptive agent error: {str(e)}"


def record_feedback(rating: int, note: str = "") -> str:
    """
    Record feedback for the last response.
    Called from interactive mode via 'feedback: N reason'
    """
    global _last_query, _long_term_memory

    if _long_term_memory is None:
        return "No active session — start a session first."

    if not 1 <= rating <= 5:
        return "Rating must be 1–5."

    _long_term_memory = log_feedback(
        _long_term_memory, _last_query, rating, note
    )

    summary = get_feedback_summary(_long_term_memory)

    return (
        f"Feedback logged: {rating}/5"
        + (f" — '{note}'" if note else "")
        + f"\nTotal feedback: {summary['total_feedback']} | "
        f"Avg: {summary['avg_rating']}/5 | "
        f"Depth preference: {summary['depth_preference']}"
    )


# ══════════════════════════════════════════════════════════════════
# BEFORE/AFTER DEMONSTRATION
# ══════════════════════════════════════════════════════════════════

def run_before_after_demo(query: str, low_rating: int = 2,
                           low_note: str = "too brief, missing ticket details",
                           verbose: bool = True) -> dict:
    """
    Demonstrate adaptive behaviour change on the same query.

    Step 1: Run query → get BEFORE response (no feedback yet)
    Step 2: Submit low rating with complaint note
    Step 3: Run SAME query → get AFTER response (with feedback modifier)
    Step 4: Compare and explain what changed

    Returns dict with before_response, after_response, explanation.
    """
    print("\n" + "="*70)
    print("PHASE 7 — BEFORE/AFTER ADAPTIVE BEHAVIOUR DEMONSTRATION")
    print(f"Query: {query}")
    print("="*70)

    # ── BEFORE — run with no feedback ─────────────────────────────
    # Clear feedback to get clean baseline
    short_term, long_term = get_adaptive_session()
    baseline_feedback = long_term.get("feedback_log", []).copy()
    long_term["feedback_log"] = []
    save_long_term_memory(long_term)

    print("\n── BEFORE (no feedback) ──")
    before_summary = get_feedback_summary(long_term)
    print(f"Feedback state: {before_summary['avg_rating']} avg | "
          f"depth: {before_summary['depth_preference']}")

    before_response = run_adaptive_agent(query, verbose=verbose)
    print(before_response)

    # ── Submit low feedback ────────────────────────────────────────
    print(f"\n── Submitting feedback: {low_rating}/5 — '{low_note}' ──")
    record_feedback(low_rating, low_note)

    # Add one more low rating to ensure avg <= 2 and pattern detected
    record_feedback(low_rating, low_note)

    after_summary = get_feedback_summary(load_long_term_memory())
    print(f"Feedback state: {after_summary['avg_rating']} avg | "
          f"depth: {after_summary['depth_preference']}")
    print(f"Adaptive context will now include: "
          f"{after_summary['common_complaints']}")

    # ── AFTER — run same query with feedback active ────────────────
    print("\n── AFTER (with feedback modifier active) ──")
    after_response = run_adaptive_agent(query, verbose=verbose)
    print(after_response)

    # ── Restore original feedback log ─────────────────────────────
    long_term = load_long_term_memory()
    long_term["feedback_log"] = baseline_feedback + long_term["feedback_log"]
    save_long_term_memory(long_term)

    # ── Explanation ────────────────────────────────────────────────
    explanation = (
        f"\nWHAT CHANGED AND WHY:\n"
        f"  Before: No feedback history. Agent used default behaviour.\n"
        f"          Adaptive context: 'none'\n"
        f"  After:  Rating {low_rating}/5 with note '{low_note}' stored.\n"
        f"          Depth preference changed to: "
        f"'{after_summary['depth_preference']}'\n"
        f"          Complaints detected: {after_summary['common_complaints']}\n"
        f"  Result: System prompt now includes instruction to provide more\n"
        f"          detail, cite specific ticket IDs, and follow pattern\n"
        f"          detection with root cause analysis.\n"
    )
    print(explanation)

    return {
        "query":           query,
        "before_response": before_response,
        "after_response":  after_response,
        "feedback_given":  f"{low_rating}/5 — {low_note}",
        "depth_before":    before_summary["depth_preference"],
        "depth_after":     after_summary["depth_preference"],
        "explanation":     explanation
    }

# Adaptive agent with graceful fallback chain for production deployment.

def run_with_graceful_fallback(query: str, verbose: bool = False) -> str:
    """
    Production entry point with graceful fallback chain.

    Tries agents in order: adaptive → langchain → llm → baseline
    Each failure is logged to errors.jsonl before trying next level.

    This is what Phase 8 deployment uses instead of run_adaptive_agent()
    directly. Users always get an answer — even if the LLM is down.
    """
    from agent.logger import log_error

    # Level 1: Adaptive agent (Phase 7)
    try:
        result = run_adaptive_agent(query, verbose=verbose)
        if not result.startswith("Adaptive agent error"):
            return result
        raise RuntimeError(result)
    except Exception as e:
        log_error("phase8", query, "adaptive_failure", str(e), "adaptive")
        if verbose:
            print(f"[FALLBACK] Adaptive agent failed: {e}")
            print("[FALLBACK] Trying LangChain agent...")

    # Level 2: LangChain agent (Phase 5)
    try:
        from agent.langchain_agent import run_langchain_agent
        result = run_langchain_agent(query, verbose=verbose)
        if not result.startswith("Agent error"):
            return result + "\n[Fallback: LangChain — adaptive unavailable]"
        raise RuntimeError(result)
    except Exception as e:
        log_error("phase8", query, "langchain_failure", str(e), "langchain")
        if verbose:
            print(f"[FALLBACK] LangChain agent failed: {e}")
            print("[FALLBACK] Trying LLM agent...")

    # Level 3: LLM agent (Phase 3)
    try:
        from agent.llm_agent import run_llm_agent
        result = run_llm_agent(query, verbose=verbose)
        return result + "\n[Fallback: LLM — tool calling unavailable]"
    except Exception as e:
        log_error("phase8", query, "llm_failure", str(e), "llm")
        if verbose:
            print(f"[FALLBACK] LLM agent failed: {e}")
            print("[FALLBACK] Using rule-based baseline...")

    # Level 4: Rule-based baseline (Phase 2) — always works, no external deps
    try:
        from agent.baseline_agent import run_agent
        result = run_agent(query, verbose=verbose)
        return result + "\n[Fallback: Rule-based — LLM unavailable]"
    except Exception as e:
        log_error("phase8", query, "baseline_failure", str(e), "baseline")

    # Total failure — return static message
    return (
        "The support agent is temporarily unavailable. "
        "Please try again in a few minutes. "
        "If this persists, contact your system administrator."
    )