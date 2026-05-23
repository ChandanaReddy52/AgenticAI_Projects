# Phase 7 — Observability Artifacts
## What the logs reveal and how to read adaptive behaviour

---

## New fields in Phase 7 log entries

Phase 6 notes field:
```
"notes": "tools:1 session:5 history_len:4"
```

Phase 7 notes field:
```
"notes": "tools:2 feedback_avg:2.6 depth:detailed history_len:4"
```

Three fields replace `session` with `feedback_avg` and `depth`. These
are the primary observability signals for adaptive behaviour. Every
adaptation decision the agent made is visible in these two values.

---

## Reading `feedback_avg` — the adaptation trigger

`feedback_avg` is the rolling average of all ratings stored in
`feedback_log` inside `long_term_memory.json`. It is computed by
`get_feedback_summary()` at the start of every agent call.

```
feedback_avg: None   → no feedback stored yet → default behaviour
feedback_avg: 2.0    → low (≤2) → depth_preference switches to "detailed"
feedback_avg: 2.6    → below threshold → "detailed" remains active
feedback_avg: 4.0+   → high → depth_preference switches to "concise" or "neutral"
```

From your logs, the transition is visible at exactly the right point:

```
Line 121: feedback_avg: None   → 1 tool called (detect_patterns only)
Line 122: feedback_avg: 2.0    → 2 tools called (detect_patterns + cross_ticket)
```

One feedback entry of rating 2 changed `feedback_avg` from `None` to `2.0`.
That single change caused the agent to call an additional tool. The causal
chain from feedback to behaviour change is captured in a single log line
comparison.

---

## Reading `depth` — the active behaviour mode

`depth` is the `depth_preference` string computed by `get_feedback_summary()`:

```
depth: neutral   → no feedback or mixed — use default tool strategy
depth: detailed  → avg ≤ 2.5 or "brief"/"shallow" in notes → call more tools,
                   cite more evidence, follow detect_patterns with cross_ticket
depth: concise   → "too long" or "concise" in notes → single tool, lead with
                   key finding, skip elaboration
```

In your logs, `depth: detailed` appears on lines 122–136 — every single
Phase 7 call after the first feedback entry. This means the adaptation
was active and stable across the entire test sequence.

The two neutral entries (lines 121 and 124) are the clean baseline:
line 121 is before any feedback, line 124 is the mid-demo reset where
feedback was temporarily cleared to demonstrate the before state.

---

## The before/after signal — lines 121 vs 122

This is the most important two-line comparison in your Phase 7 logs:

```
Line 121:
  tools: 1     feedback_avg: None   depth: neutral
  → detect_patterns called, agent stopped

Line 122:
  tools: 2     feedback_avg: 2.0    depth: detailed
  → detect_patterns called, then cross_ticket_analysis called
```

Everything else between these two calls was identical — same query, same
data, same ChromaDB collections, same LLM model. The only thing that changed
was `feedback_avg` moving from `None` to `2.0` and `depth` moving from
`neutral` to `detailed`. That change injected a new instruction block into
the system prompt, which caused the LLM to call a second tool.

---

## The demo cycle signal — lines 124 vs 125

Lines 124 and 125 show the automated `demo adaptive` function working:

```
Line 124: feedback_avg: None   depth: neutral   tools: 1
          ← feedback temporarily cleared for BEFORE state

Line 125: feedback_avg: 2.0    depth: detailed  tools: 2
          ← feedback restored for AFTER state
```

This pair is the cleanest before/after evidence because it was a controlled
test — same session, same query, feedback state toggled between the two calls.

---

## Reading `adaptive_context` in response_keys

Every Phase 7 log entry has `adaptive_context` in `response_keys`. This field
stores the first 200 characters of the instruction string that was injected
into the system prompt. When `depth: neutral`, this field contains `"none"`.
When `depth: detailed`, it contains the beginning of the instruction:
`"User feedback indicates responses are too brief. Provide MORE detail..."`.

This field confirms the instruction was actually injected — not just computed.
The LLM received the instruction and acted on it. The tool count increase is
the proof it was followed.

---

## Summary: what to look for in interactions.jsonl for Phase 7

| Signal | Where | What it proves |
|--------|-------|---------------|
| `feedback_avg: None` → `2.0` between two entries | notes field | Feedback stored and loaded correctly |
| `depth: neutral` → `depth: detailed` | notes field | Adaptation triggered |
| `tools:1` → `tools:2` on same query | notes field | Behaviour changed — more tools called |
| `depth: detailed` stable across all eval entries | lines 126–135 | Adaptation persists across sessions |
| `tools:2` on Q2 in BOTH eval runs | lines 127, 132 | Stable behaviour change, not one-off |
| `adaptive_context` non-empty | response_keys | Instruction injected into prompt |
| Lines 124 vs 125 | notes comparison | Controlled before/after in same session |
