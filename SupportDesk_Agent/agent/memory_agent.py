"""
memory_agent.py — Phase 6 orchestrator with memory + planning

Adds to Phase 5 LangChain agent:
  1. Short-term memory: ConversationBufferWindowMemory
     — conversation history injected into every prompt
     — "tell me more about that customer" works correctly

  2. Long-term memory: JSON persistence
     — escalations, resolved patterns, customer notes survive sessions
     — memory context injected into system prompt

  3. Multi-step planning: for complex queries
     — agent breaks task into steps and calls multiple tools
     — Q2 fix: detect_patterns THEN cross_ticket_analysis

  4. Memory reset: 'reset memory' command clears short-term
     — long-term memory is preserved across resets
"""

import json, os, time
from dotenv import load_dotenv


def _find_env(start: str):
    import os as _os
    current = start
    for _ in range(6):
        c = _os.path.join(current, ".env")
        if _os.path.isfile(c): return c
        parent = _os.path.dirname(current)
        if parent == current: break
        current = parent
    return None


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
env = _find_env(PROJECT_ROOT)
if env: load_dotenv(env)

from langchain_openai import ChatOpenAI
from langchain.agents  import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.safety          import check_safety
from agent.logger          import log_interaction
from agent.tool_safeguards import ToolCallTracker, check_tool_input, validate_tool_output
from agent.tools_langchain import ALL_TOOLS
from agent.memory_store    import (
    create_short_term_memory, load_long_term_memory,
    save_long_term_memory, log_escalation,
    log_resolved_pattern, add_customer_note,
    log_feedback, build_memory_context
)


# ── Memory retention rules ────────────────────────────────────────
MEMORY_RETENTION_RULES = """
MEMORY RETENTION RULES:
- Short-term memory resets when user types 'reset memory'
- Long-term memory (escalations, patterns, notes) persists across sessions
- Do NOT retain: personal data, passwords, sensitive PII
- DO retain: ticket IDs discussed, customer names, patterns identified,
             recommendations made, escalations flagged
"""


def _build_memory_agent(memory_context: str,
                         short_term_memory):
    """
    Build LangChain agent with memory injected into system prompt
    and conversation history injected via MessagesPlaceholder.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    system_prompt = f"""You are a support intelligence agent for GlobalFoods Inc.
You have access to 5 tools that analyze support tickets and customer data.
You have memory of this conversation and prior sessions.

{memory_context}

{MEMORY_RETENTION_RULES}

TOOL SELECTION RULES:
1. Ticket ID specified (TKT-XXXX) → analyze_ticket
2. Patterns, trends, recurring issues → detect_patterns
   If customer name mentioned → use window='7d'
3. Customer health, churn, who to call → rank_customer_risk (top_n=5)
4. SLA deadlines, breach timing → predict_sla_risk
5. Root cause, general urgency, summaries → cross_ticket_analysis

MULTI-STEP PLANNING:
For complex questions requiring multiple perspectives, call tools in sequence:
- Customer + pattern question → rank_customer_risk THEN detect_patterns
- Urgency + root cause → cross_ticket_analysis THEN predict_sla_risk
Always synthesise results from multiple tools into one coherent answer.

MEMORY USAGE:
- Reference conversation history when user says 'that ticket', 'the customer',
  'tell me more', 'what about', or any pronoun referring to prior context.
- If user references something from earlier, use it — do not ask again.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),   # short-term memory injected here
        ("human",  "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(
        llm=llm, tools=ALL_TOOLS, prompt=prompt
    )

    return agent


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


# ── Session state ──────────────────────────────────────────────────
_short_term_memory = None
_long_term_memory  = None


def init_session() -> tuple:
    """
    Initialise a new session.
    Loads long-term memory, creates fresh short-term memory.
    Updates session count.
    Returns (short_term, long_term).
    """
    global _short_term_memory, _long_term_memory

    lt = load_long_term_memory()
    lt["session_count"] = lt.get("session_count", 0) + 1
    lt["last_session"]  = __import__("datetime").datetime.now().isoformat()
    save_long_term_memory(lt)

    st = create_short_term_memory()

    _short_term_memory = st
    _long_term_memory  = lt

    return st, lt


def get_session_memory() -> tuple:
    """Get current session memory, initialising if needed."""
    global _short_term_memory, _long_term_memory
    if _short_term_memory is None or _long_term_memory is None:
        return init_session()
    return _short_term_memory, _long_term_memory


def reset_short_term_memory() -> str:
    """Reset short-term memory. Long-term memory is preserved."""
    global _short_term_memory
    _short_term_memory = create_short_term_memory()
    return "Short-term memory cleared. Long-term memory (escalations, notes, patterns) preserved."


def run_memory_agent(query: str, verbose: bool = False) -> str:
    start = time.time()

    # Safety check
    safety_status, safety_msg = check_safety(query)
    if safety_status == "unsafe":
        return f"🚫 SAFETY BLOCK: {safety_msg}"
    if safety_status == "escalate":
        return f"⚠️  ESCALATION FLAGGED: {safety_msg}"

    # Get session memory
    short_term, long_term = get_session_memory()

    # Build memory context for system prompt
    memory_context = build_memory_context(long_term)

    tracker = ToolCallTracker()

    try:
        agent         = _build_memory_agent(memory_context, short_term)
        guarded_tools = _wrap_tools(ALL_TOOLS, tracker)

        executor = AgentExecutor(
            agent=agent,
            tools=guarded_tools,
            memory=short_term,           # ← short-term memory attached here
            verbose=verbose,
            max_iterations=5,            # slightly higher for multi-step plans
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

        response      = result.get("output", "No response generated.")
        total_latency = time.time() - start
        tool_summary  = tracker.summary()

        if verbose:
            print(f"\n[MEMORY AGENT] Tools: {tool_summary}")
            print(f"[MEMORY AGENT] Total: {round(total_latency*1000)}ms")
            print(f"[MEMORY AGENT] Session: #{long_term['session_count']}")

        # Auto-detect escalations in response and log to long-term memory
        _auto_log_escalations(response, long_term)

        log_interaction(
            query=query,
            intent="memory_agent",
            tool=", ".join([tc["tool"] for tc in tool_calls]) or "none",
            response={
                "output":         response[:500],
                "tool_calls":     tool_calls,
                "tool_summary":   tool_summary,
                "session":        long_term["session_count"],
                "memory_context": memory_context[:200],
                "hallucination_check": True
            },
            latency=total_latency,
            phase="phase6_memory",
            notes=(f"tools:{tool_summary['total_calls']} "
                   f"session:{long_term['session_count']} "
                   f"history_len:{len(short_term.chat_memory.messages)}")
        )

        footer = (
            f"\n[Phase 6 Memory | {round(total_latency*1000)}ms | "
            f"Tools: {tool_summary['total_calls']} | "
            f"History: {len(short_term.chat_memory.messages)} msgs | "
            f"Session: #{long_term['session_count']}]"
        )
        return response + footer

    except Exception as e:
        return f"Memory agent error: {str(e)}"


def _auto_log_escalations(response: str, long_term: dict) -> None:
    """
    Scan agent response for escalation signals and auto-log to long-term memory.
    Looks for: "executive escalation", "VP CS", "critical" + customer name.
    """
    import re
    response_lower = response.lower()

    # Check for critical customer mentions
    customer_map = {
        "freshmart":  "CUST-002",
        "globalfoods": "CUST-001",
        "logix pharma": "CUST-003",
        "quickship":  "CUST-004",
        "agrisource": "CUST-005",
    }

    if "executive escalation" in response_lower or "contact vp" in response_lower:
        for name, cid in customer_map.items():
            if name in response_lower:
                # Check not already logged recently
                recent = [e for e in long_term["escalations"]
                          if e["customer"] == cid
                          and not e["resolved"]]
                if not recent:
                    log_escalation(long_term, "auto-detected", cid)
                break