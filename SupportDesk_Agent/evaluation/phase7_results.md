# Phase 7 — Adaptive Behaviour Results
## Capstone: AI Support Intelligence Agent — GlobalFoods Inc.
**Run date:** 5 May 2026
**Framework:** LangChain + ConversationBufferWindowMemory + Feedback Adaptation
**Model:** GPT-4o-mini | **Feedback entries used:** 5 ratings | **Avg rating:** 2.6/5

---

## 1. BEFORE/AFTER COMPARISON — Q2 FreshMart Patterns

This is the primary Phase 7 evidence. Same query, same data, different
behaviour because of stored feedback.

### BEFORE — line 121 (`feedback_avg: None`, `depth: neutral`)
```
Query:          "Is there a pattern forming across FreshMart tickets?"
tools_called:   1  (detect_patterns only)
feedback_avg:   None  (no feedback stored yet)
depth:          neutral
latency_ms:     17,946
adaptive_context: none
```
**Behaviour:** Default. Single tool. Agent called `detect_patterns` and stopped.
No follow-up root cause analysis. Adaptive context block in system prompt read:
`"[No feedback received yet — using default behaviour]"`

### AFTER — line 122 (`feedback_avg: 2.0`, `depth: detailed`)
```
Query:          "Is there a pattern forming across FreshMart tickets?"
tools_called:   2  (detect_patterns + cross_ticket_analysis)
feedback_avg:   2.0
depth:          detailed
latency_ms:     26,443
adaptive_context: "User feedback indicates responses are too brief.
                   Provide MORE detail: cite more ticket IDs, include
                   more evidence quotes..."
```
**Behaviour:** Changed. Two tools called. Agent called `detect_patterns` then
immediately followed with `cross_ticket_analysis` to add root cause depth.
The adaptive context injected into the system prompt instructed more detail
and pattern follow-up. The agent obeyed.

### What changed and why

| Dimension | Before | After | Change |
|-----------|--------|-------|--------|
| Tools called | 1 | 2 | +1 tool |
| `depth_preference` | neutral | detailed | Feedback triggered |
| Adaptive context | none | "provide MORE detail" | Injected from feedback |
| Latency | 17,946ms | 26,443ms | +47% (second tool call) |
| Evidence depth | Pattern only | Pattern + root cause | ✅ Richer |

**The adaptation mechanism:** Rating `2/5` with note `"too brief, missing
ticket details"` stored in `feedback_log`. `get_feedback_summary()` computed
`avg_rating: 2.0` and detected `"brief"` in the note → set
`depth_preference: "detailed"`. `build_adaptive_context()` returned an
instruction string. That string was injected into the system prompt on the
next call. The LLM read it and called a second tool.

---

## 2. FEEDBACK COLLECTION VERIFIED

| Line | Query | feedback_avg at time | depth |
|------|-------|---------------------|-------|
| 121 | Q2 first run | None | neutral |
| 122 | Q2 after feedback | 2.0 | detailed |
| 123 | Q2 repeat in same session | 2.0 | detailed |
| 124 | Q2 (demo — feedback cleared) | None | neutral |
| 125 | Q2 (demo — feedback restored) | 2.0 | detailed |
| 126 | Eval Q1 | 2.6 | detailed |
| 127 | Eval Q2 | 2.6 | detailed |
| 128 | Eval Q3 | 2.6 | detailed |
| 129 | Eval Q4 | 2.6 | detailed |
| 130 | Eval Q5 | 2.6 | detailed |

**Key observations:**
- Lines 124 vs 125 demonstrate the before/after demo function working:
  feedback cleared → `None/neutral` → feedback restored → `2.0/detailed`
- Lines 126–130: `feedback_avg: 2.6` and `depth: detailed` persisted across
  the entire eval run — proving feedback from prior sessions is loaded at
  session start and applied to every subsequent query
- `depth: detailed` remained stable across both eval runs (lines 126–135)
  confirming the adaptation is not a one-off — it is the new default until
  feedback changes it

---

## 3. ADAPTATION PERSISTS ACROSS EVAL RUNS

### First eval run — lines 126–130

| Query | Tool(s) | feedback_avg | depth | Latency (ms) |
|-------|---------|-------------|-------|-------------|
| Q1 | cross_ticket_analysis | 2.6 | detailed | 16,522 |
| Q2 | detect_patterns + cross_ticket_analysis | 2.6 | detailed | 22,310 |
| Q3 | rank_customer_risk | 2.6 | detailed | 6,047 |
| Q4 | predict_sla_risk | 2.6 | detailed | 7,567 |
| Q5 | cross_ticket_analysis | 2.6 | detailed | 13,874 |

### Second eval run — lines 131–135

| Query | Tool(s) | feedback_avg | depth | Latency (ms) |
|-------|---------|-------------|-------|-------------|
| Q1 | cross_ticket_analysis | 2.6 | detailed | 12,834 |
| Q2 | detect_patterns + cross_ticket_analysis | 2.6 | detailed | 19,246 |
| Q3 | rank_customer_risk | 2.6 | detailed | 5,892 |
| Q4 | predict_sla_risk | 2.6 | detailed | 7,449 |
| Q5 | cross_ticket_analysis | 2.6 | detailed | 15,546 |

**Q2 calling 2 tools in BOTH eval runs** confirms the behaviour change is
stable and persists across sessions, not just within a single interactive run.

**history_len grows correctly in both runs:**
Q1: 2 → Q2: 4 → Q3: 6 → Q4: 8 → Q5: 10
Memory accumulation from Phase 6 is intact alongside adaptation.

---

## 4. TOOL SELECTION ACCURACY

All 5 queries correct across both eval runs:

| Query | Expected | Actual | Correct? |
|-------|---------|--------|---------|
| Q1 | cross_ticket_analysis | cross_ticket_analysis | ✅ |
| Q2 | detect_patterns (+ follow-up) | detect_patterns + cross_ticket_analysis | ✅ |
| Q3 | rank_customer_risk | rank_customer_risk | ✅ |
| Q4 | predict_sla_risk | predict_sla_risk | ✅ |
| Q5 | cross_ticket_analysis | cross_ticket_analysis | ✅ |

**Tool selection accuracy: 5/5 (100%) — unchanged from Phase 5 and 6.**
Phase 7 adaptation changes *how* tools are used (depth, follow-up calls),
not *which* tool is selected for the primary intent.

---

## 5. PHASE 6 vs PHASE 7 QUALITY COMPARISON

| Metric | Phase 6 | Phase 7 |
|--------|---------|---------|
| Q2 tools called | 2 (after multi-turn) | 2 (on every call after feedback) |
| Q2 multi-step trigger | Required prior context in memory | Triggered by feedback signal alone |
| Depth adaptation | None | ✅ detailed mode active |
| Feedback loop | Logged but ignored | ✅ Modifies system prompt |
| Adaptive context in prompt | Not present | ✅ Injected from feedback_log |
| `depth` field in logs | Not present | ✅ Shows current adaptation state |
| Q1 latency | 13,127ms | 16,522ms (first eval) |
| Q2 latency | 14,673ms | 22,310ms (first eval) |
| Q5 consistency | 9 tickets, $3.1M | 9 tickets, $3.1M ✅ stable |

**Key distinction:** In Phase 6, multi-step Q2 only happened when the user
had already asked about FreshMart in a prior turn (memory context). In Phase 7,
multi-step Q2 happens on the FIRST query of the session because the feedback
signal from `long_term_memory.json` is loaded at startup and injected before
any tool is called. Memory-triggered vs feedback-triggered multi-step planning.

---

## 6. AVERAGE LATENCY COMPARISON ACROSS ALL PHASES

| Phase | Avg latency (5-query eval) |
|-------|--------------------------|
| Phase 2 (baseline) | <5ms |
| Phase 3 (LLM V2) | 5,893ms |
| Phase 4 (RAG) | 7,310ms |
| Phase 5 (LangChain) | 10,535ms |
| Phase 6 (Memory) | 12,806ms |
| Phase 7 eval run 1 | 13,264ms |
| Phase 7 eval run 2 | 12,194ms |

Phase 7 adds ~400ms overhead vs Phase 6 — the cost of loading, analysing,
and injecting the feedback context into the system prompt. This is negligible
relative to the LLM call latency and is not an operational concern.

---

## 7. NEW FAILURE MODES IN PHASE 7

**Failure Mode 1 — Adaptation applies globally, not per-query-type**
`depth: detailed` was triggered by a low rating on Q2 (pattern detection).
That same `depth: detailed` was then applied to Q3 (customer ranking) and Q4
(SLA risk) — queries that were not rated poorly. The feedback modifier is
global: one low rating affects all subsequent queries regardless of intent.
A more precise implementation would map feedback to specific tool types
(low rating on `detect_patterns` → only affects `detect_patterns` calls).

**Failure Mode 2 — avg_rating does not reset after high ratings**
Once `feedback_avg` drops to 2.0 or 2.6, it stays low even if subsequent
ratings are 4 or 5. The rolling average smooths over improvements slowly.
After 2 ratings of 2.0 and 1 rating of 5.0, the average is 3.0 — still
`depth: detailed`. The agent would need 3–4 high ratings to shift back to
neutral. A recency-weighted average (recent ratings count more) would make
adaptation more responsive to improvement.

**Failure Mode 3 — No feedback on Q3, Q4, Q5 in the demo run**
Lines 128–130: Q3, Q4, Q5 all have `feedback_avg: 2.6` inherited from
the Q2 feedback. No feedback was recorded for these queries specifically.
The `record_feedback()` function attributes feedback to `_last_query` —
whatever was last asked. If the user gives feedback after Q5 without typing
the query explicitly, it is attributed to Q5. This is correct but means
feedback attribution depends on the user remembering to rate immediately
after each response.
