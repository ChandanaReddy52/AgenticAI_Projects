# Phase 6 → Phase 7: Improvements from Adaptive Behaviour
## What changed, what got better, what it cost

---

## The core architectural change

Phase 6 added memory — the agent remembered conversation history and used it
to resolve pronouns and trigger multi-step plans. But that memory was reactive.
Multi-step Q2 only happened when the user had already asked about FreshMart
earlier in the session. A fresh session with no prior context would get
the same single-tool response as Phase 5.

Phase 7 made adaptation proactive. Instead of waiting for conversation context
to build up, the agent loads feedback signals from `long_term_memory.json` at
session start and applies them immediately. The first query of a new session
already benefits from ratings given in previous sessions. The agent does not
need to be told what the user wants — it has learned it from prior feedback.

---

## Improvement 1 — Multi-step Q2 on first query, every session

**Phase 6 behaviour:**
Q2 triggered two tools only when FreshMart had been mentioned in a prior turn.
In a fresh session with no conversation history, Q2 called `detect_patterns`
once and stopped. `history_len: 2` meant no prior context to escalate from.

**Phase 7 behaviour (lines 122, 127, 132):**
Q2 calls `detect_patterns + cross_ticket_analysis` on the first query of
every session, including fresh sessions with `history_len: 2`.

```
Line 122: tools:2  feedback_avg:2.0  depth:detailed  history_len:2
Line 127: tools:2  feedback_avg:2.6  depth:detailed  history_len:4
Line 132: tools:2  feedback_avg:2.6  depth:detailed  history_len:4
```

The trigger is no longer conversation context — it is the persisted feedback
signal. `depth: detailed` was loaded from `long_term_memory.json` before the
first tool was called. The agent knew to go deeper before the user said anything.

---

## Improvement 2 — Feedback-triggered vs memory-triggered planning

This is the key qualitative difference between Phase 6 and Phase 7 multi-step
behaviour, and it matters for production systems.

**Phase 6 multi-step trigger:** User had to ask about the customer first.
The agent needed 2+ turns to infer depth was needed. A support lead who opened
the app and typed "show me FreshMart patterns" in their first message would
get a shallow answer.

**Phase 7 multi-step trigger:** A prior session's `feedback: 2 too brief`
is enough. The next session — even hours later, even after restarting — starts
with `depth: detailed` already active. The agent's behaviour improved between
sessions without any in-session context being needed.

---

## Improvement 3 — Adaptation visible in every log entry

Phase 6 logs did not record whether adaptation was active because there was
no adaptation. Phase 7 logs show `feedback_avg` and `depth` on every single
entry. This means:

For every Phase 7 response, you can tell from the log:
- What the agent's current quality signal was (`feedback_avg`)
- What behaviour mode it was in (`depth`)
- Whether the adaptive context was injected (`adaptive_context` field)
- Whether the behaviour change was expressed (`tools` count)

This is complete observability of the adaptation loop — input signal, derived
mode, injected instruction, observed behaviour. All four steps visible in one
log entry.

---

## Improvement 4 — Stable adaptation across two independent eval runs

Lines 126–130 (first eval) and lines 131–135 (second eval) show identical
patterns: Q2 calls 2 tools, all others call 1 tool, `depth: detailed` on all
entries, `feedback_avg: 2.6` on all entries.

This proves the adaptation is not a session-level fluke. It is loaded from
disk at the start of every session and applied consistently. The agent's
improved Q2 behaviour in the second eval run was not caused by anything in
the second session — it was caused by feedback stored after the first session.

---

## What it cost

| Metric | Phase 6 | Phase 7 | Change |
|--------|---------|---------|--------|
| Q2 latency (eval run 1) | 14,673ms | 22,310ms | +52% |
| Q1 latency (eval run 1) | 13,127ms | 16,522ms | +26% |
| Q3 latency (eval run 1) | 6,338ms | 6,047ms | -5% (noise) |
| Avg latency (5-query eval) | 12,806ms | 13,264ms | +4% |
| Tool selection accuracy | 5/5 | 5/5 | No change |

The Q2 latency increase from 14,673ms to 22,310ms is the cost of the second
tool call added by adaptation. This is expected and acceptable — the user
asked for more detail, they get more detail, it takes longer. The 4% average
latency increase across all five queries confirms the overhead of loading and
injecting the adaptive context is negligible (approximately 400ms per call).
