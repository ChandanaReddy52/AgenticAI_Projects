# Phase 5 → Phase 6: Improvements from Memory
## What changed, what got better, what it cost

---

## The core architectural change

Phase 5 treated every query as independent. Each call to `run_langchain_agent()`
created a new agent, called one tool, returned an answer, and discarded everything.
The agent had no awareness that a previous query had been asked, what the answer
was, or who the user had been asking about.

Phase 6 added a persistent conversation buffer. Every query and response is
stored in `ConversationBufferWindowMemory`. On the next query, the full buffer
is injected into the system prompt via `MessagesPlaceholder("chat_history")`.
The LLM now sees the conversation as a thread — not as isolated questions.

---

## Improvement 1 — Pronoun resolution

**Phase 5 behaviour:**
```
Turn 1: "Which customer is most at risk of churning?"
→ FreshMart Retail Group — CRITICAL, risk score 78.5

Turn 2: "Tell me more about their open tickets"
→ Agent: "Could you clarify which customer you are referring to?"
```
No memory of Turn 1. "Their" was unresolvable.

**Phase 6 behaviour (log lines 107–108):**
```
Turn 1: "Which customer is most at risk of churning?"
→ FreshMart Retail Group — CRITICAL
   history_len: 2

Turn 2: "Tell me more about their open tickets"
→ Agent calls detect_patterns + cross_ticket_analysis on FreshMart
   history_len: 4
   tools: 2
```

The agent resolved "their" to FreshMart from the Turn 1 context in the buffer.
It then immediately escalated to a two-tool plan — pattern detection AND root
cause analysis — because it now knew which customer was being asked about.
This is qualitatively different from any prior phase.

---

## Improvement 2 — Multi-step planning on follow-up queries

**Phase 5:** Every query called exactly one tool regardless of complexity.
"Is there a pattern forming across FreshMart tickets?" → `detect_patterns` → one result.

**Phase 6:** With customer context in memory, the agent recognised that
"tell me more about their tickets" required both pattern detection (what tags
are clustering?) and root cause synthesis (why is this happening?). It called
both tools in sequence and synthesised the results into one answer.

From the logs:
```
Phase 5 Q2: tools:1  (detect_patterns only)
Phase 6 T2: tools:2  (detect_patterns + cross_ticket_analysis)
```

The multi-step plan only emerged because memory gave the agent enough context
to understand the question was asking for depth, not just a surface pattern.

---

## Improvement 3 — Session continuity across the full evaluation

In Phase 5, running `--run-eval` produced five independent responses.
Q3 answer had no awareness of what Q1 or Q2 had found.

In Phase 6, the history_len grows across every query in the evaluation:
```
Q1: history_len 2   → Q1 alone in buffer
Q2: history_len 4   → Q1 + Q2 in buffer
Q3: history_len 6   → Q1 + Q2 + Q3 in buffer
Q4: history_len 8   → Q1 + Q2 + Q3 + Q4 in buffer
Q5: history_len 10  → Q1 + Q2 + Q3 + Q4 + Q5 in buffer
```

By Q5, when asked "what is the root cause across sync tickets?", the agent
had full context of the prior four queries. Its answer could reference the
FreshMart risk identified in Q3, the SLA breach found in Q4, and the patterns
from Q2 — without any of that being explicitly restated.

---

## Improvement 4 — Graceful reset with context preservation

Phase 5 had no memory to reset — every query was already stateless.

Phase 6 introduced a two-tier reset: `reset memory` clears the short-term
conversation buffer while long-term memory (session count, escalation log,
customer notes) is preserved. After reset, the agent correctly identifies that
context has been lost and asks for clarification rather than guessing.

From log line 113:
```
query: "Tell me more about that customer"
tool_called: none
latency_ms: 1,092
history_len: 2
```
Under 2 seconds. No tool call. The agent asked "which customer?" — correct
behaviour because "that customer" is now unresolvable.

---

## What it cost

| Metric | Phase 5 | Phase 6 | Change |
|--------|---------|---------|--------|
| Avg latency (5-query eval) | 10,535ms | 12,806ms | +22% |
| Multi-step query latency | N/A | 27,768ms avg | New overhead |
| Tool selection accuracy | 5/5 | 5/5 | No change |
| Queries requiring clarification | None | 1 (post-reset) | Expected |

The 22% latency increase on single-tool queries comes from injecting the
conversation history into every prompt — even when the history is short.
As `history_len` grows toward the window limit of 12, token count increases
and latency rises incrementally.

The 27-second latency on multi-step queries is the most significant cost.
Two sequential tool calls, each making a full LLM round trip, plus a synthesis
call, adds up. For a support lead reviewing a morning queue, 28 seconds per
follow-up question is operationally high. Session-level result caching is the
mitigation — if detect_patterns has already been called for FreshMart in this
session, re-use the result instead of making a new call.
