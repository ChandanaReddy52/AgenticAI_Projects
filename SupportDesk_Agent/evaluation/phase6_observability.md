# Phase 6 — Observability Artifacts
## What the logs reveal and how to use them

---

## What changed in Phase 6 logs vs Phase 5

Phase 5 log entries had a `notes` field that showed:
```
"notes": "tools_called:1 tools:['rank_customer_risk']"
```

Phase 6 entries added two new fields to `notes`:
```
"notes": "tools:2 session:4 history_len:4"
```

These two new fields — `session` and `history_len` — are the primary
observability signals for memory behaviour. Everything that matters about
whether memory is working can be read from these two numbers.

---

## Reading `history_len` — the memory proof

`history_len` records how many messages are in the
`ConversationBufferWindowMemory` at the moment the tool call is logged.
Each turn adds 2 messages: the user query and the agent response.

```
Turn 1: history_len: 2   → 1 exchange in buffer (current query + response)
Turn 2: history_len: 4   → 2 exchanges in buffer
Turn 3: history_len: 6   → 3 exchanges in buffer
...
Turn 6: history_len: 12  → hits WINDOW_SIZE=6 — oldest messages start dropping
```

From your actual logs, the first eval run (session 3, lines 101–106):
```
Q1: history_len: 2   ← session just started
Q2: history_len: 4   ← Q1 exchange in buffer
Q3: history_len: 6   ← Q1 + Q2 in buffer
Q4: history_len: 8   ← Q1 + Q2 + Q3 in buffer
Q5: history_len: 10  ← Q1 + Q2 + Q3 + Q4 in buffer
```

This growth pattern is the proof that memory is accumulating correctly.
If `history_len` stayed at 2 every turn, memory would not be working.

**The critical test — Turn 2 "Tell me more about their open tickets"
(lines 108, 111):**
```
history_len: 4
tool_called: detect_patterns, cross_ticket_analysis
```
`history_len: 4` means the prior customer query (Turn 1) was in the buffer.
The agent resolved "their" to FreshMart using that context. Two tools were
called — which only happened because the agent knew from memory which customer
to focus on. This single log line is the strongest evidence that memory is
functioning correctly.

---

## Reading `session` — the long-term memory proof

`session` is the `session_count` from `data/long_term_memory.json`.
It increments by 1 every time `init_session()` is called — which happens
at the start of every interactive run or evaluation run.

From your logs:
```
Session 3  → eval run         (lines 101–106)
Session 4  → multi-turn test  (lines 107–109)
Session 5  → multi-turn test  (lines 110–112)
Session 6  → single query     (line 114)
Session 7  → single query     (line 115)
Session 8  → second eval run  (lines 116–120)
```

The fact that session counts 3 through 8 appear across multiple separate
terminal runs proves that long-term memory is persisting to disk between
sessions. If `long_term_memory.json` was not being written or read correctly,
`session` would always show 1.

---

## The memory reset signal in logs

After `reset memory` was typed in session 5, the next query logged was
(line 113):
```
query:       "Tell me more about that customer"
tool_called: none
latency_ms:  1,092
history_len: 2
```

Three signals confirm reset occurred:
1. `history_len: 2` — only the current query in buffer, prior context gone
2. `tool_called: none` — agent could not resolve "that customer" to a tool call
3. `latency_ms: 1,092` — fastest response in all Phase 6 logs; no tool call,
   just the LLM asking for clarification in under 2 seconds

Without these three signals aligning, you could not confirm the reset worked.

---

## Reading multi-step tool calls

When the `tool_called` field contains a comma-separated list, the agent
called multiple tools in one turn:
```
"tool_called": "detect_patterns, cross_ticket_analysis"
"notes":       "tools:2 session:4 history_len:4"
```

This appears on lines 108 and 111 — both for "Tell me more about their
open tickets." `tools:2` in notes confirms two tools ran. The latency on
these entries (28,203ms and 27,332ms) reflects two sequential tool calls
plus a synthesis LLM call — the observable cost of multi-step planning.

Compare this to single-tool entries (e.g. line 104, Q3):
```
"tool_called": "rank_customer_risk"
"notes":       "tools:1 session:3 history_len:6"
latency_ms:    7,429
```

The latency difference (7,429ms vs 28,203ms) is the measurable overhead of
multi-step planning. This trade-off — richer answers at higher cost — is
visible directly in the observability data.

---

## Summary: what to look for in `interactions.jsonl` for Phase 6

| Signal | Where | What it proves |
|--------|-------|---------------|
| `history_len` grows +2 per turn | `notes` field | Short-term memory accumulating |
| `history_len: 4` on pronoun query | line 108, 111 | Memory correctly resolved context |
| `history_len: 2` after reset | line 113 | Short-term reset working |
| `session` count increments | `notes` field | Long-term memory persisting to disk |
| `tool_called` has comma-separated tools | log entry | Multi-step planning activated |
| `latency_ms > 25,000` | multi-tool entries | Observable cost of multi-step |
| `tool_called: none, latency < 2000` | line 113 | Agent asked for clarification |
