# Phase 4 — Observability Artifacts
## What was collected, what it tells you, and why it matters

---

## Artifact 1 — `evaluation/phase4_rag_results.md`

### What it is

A structured evidence document that captures the before/after comparison between Phase 3 (LLM without retrieval) and Phase 4 (LLM with RAG). It is filled from actual terminal outputs — not from expected values.

### What it records

**Build verification** confirms the vector store was constructed correctly before any evaluation runs. It records document counts per collection and the location of the `.env` file found by the path-walking loader. This matters because a misconfigured build (wrong document count, wrong API key source) invalidates all downstream results.

**Query-by-query comparison tables** record six dimensions for every query: tickets cited, business impact specificity, evidence quality, confidence score, latency, and retrieved doc count. Each row maps a specific Phase 3 failure to its Phase 4 outcome — whether fixed, partially fixed, or still failing. This is the primary evidence for the capstone requirement "show improvement over baseline."

**Retrieval quality table** records avg relevance score per collection type. This is the metric that explains *why* some queries improved and others did not. Queries with positive relevance (0.1–0.15) produced better answers because the retrieved context was semantically aligned. Queries with near-zero or negative relevance (Q1, Q3) retrieved documents but with no meaningful ordering — the LLM still ran, but on low-signal context.

**Failure mode documentation** captures new problems introduced by Phase 4 that did not exist in Phase 3. RAG introduces retrieval failure modes (low relevance, structural similarity making differentiation impossible) that are entirely absent from a static-injection approach. Documenting these is required for the capstone's failure analysis section.

### Why it matters for evaluation

The capstone rubric asks for evidence that retrieval improved response quality over baseline. This document provides that evidence at the query level with specific before/after data. It also demonstrates engineering judgment — the ability to distinguish between "retrieval worked and the answer improved" (Q5), "retrieval worked but a different failure persists" (Q3), and "retrieval is the wrong tool for this query type" (Q1).

---

## Artifact 2 — `logs/interactions.jsonl`

### What it is

An append-only log file where every agent interaction is recorded as a single JSON line. It is written by `agent/logger.py` after every query regardless of phase. It serves as the ground truth for all evaluation claims.

### Structure of each log entry

```json
{
  "timestamp":        "2026-04-30T14:35:11.529020",
  "phase":            "phase4_rag",
  "query":            "Q3: Which customer is most at risk of churning?",
  "intent":           "rank_customer_risk",
  "tool_called":      "rag_rank_customer_risk",
  "latency_ms":       7462.19,
  "response_keys":    ["customer_id", "name", "arr", ...],
  "hallucination_check": true,
  "confidence":       1.0,
  "notes":            "retrieved:5 avg_rel:0.0"
}
```

### What each field tells you

**`phase`** — differentiates Phase 2, Phase 3 (with strategy variant: `phase3_llm_v1`, `phase3_llm_v2`, `phase3_llm_v3`), and Phase 4 (`phase4_rag`). Enables cross-phase comparison by filtering on this field.

**`intent`** — confirms the intent router classified the query correctly. A mismatch between the query and the detected intent (e.g., Q5 in Phase 2 was routed to `analyze_ticket` instead of `cross_ticket`) is a documented routing failure — visible here without re-running the agent.

**`tool_called`** — in Phase 4, tool names are prefixed with `rag_` (e.g., `rag_cross_ticket`, `rag_rank_customer_risk`). This distinguishes RAG tool calls from Phase 3 LLM calls and Phase 2 rule calls in the same log file.

**`latency_ms`** — end-to-end wall-clock time from query receipt to response return. For Phase 4, this includes embedding lookup time + ChromaDB retrieval time + LLM call time. Comparing this to Phase 3 latency on the same query measures the overhead cost of RAG.

**`response_keys`** — the keys present in the LLM's JSON response. This is the diagnostic for schema compliance without storing full response text. For example, Q3 Phase 4 always shows `["customer_id", "name", ...]` — a single object — instead of `["ranked_customers", "total_arr_at_risk", ...]` — the expected array wrapper. The schema drift is visible here without reading the full response.

**`hallucination_check`** — a boolean set to `true` when the response was produced from grounded source data (ticket descriptions, customer fields) and `false` when the agent returned an error or safety block. All Phase 4 RAG queries with actual LLM calls show `true`. The two `exit`/`python main.py` entries (lines 60, 66) show `false` — these were safety-blocked as unknown intent.

**`confidence`** — the LLM-reported confidence value from the JSON response. In Phase 2 this is always `null` (rule-based tools hardcoded 0.4 but did not include it in the log field). In Phase 3, values range 0.5–0.9. In Phase 4, the fix to the confidence prompt template moved values from 0.0 (Phase 4 first run, lines 51–55) to meaningful values 0.7–1.0 (Phase 4 second run, lines 67–71). The jump from 0.0 to 1.0 on Q3 — on a wrong answer — is the confidence calibration failure documented in the failure modes section.

**`notes`** — Phase 4 only. Contains `retrieved:N avg_rel:X.XXXX`. This is the retrieval stats injected by `rag_agent.py` after each call. It is the primary signal for diagnosing whether a poor answer was caused by bad retrieval or bad LLM reasoning. `retrieved:12 avg_rel:0.1438` (Q5) indicates good retrieval. `retrieved:5 avg_rel:0.0` (Q3) indicates the retriever returned documents but with no semantic confidence — the problem is retrieval architecture, not LLM reasoning.

### How to use the log for cross-phase analysis

Filter by phase to get isolated comparisons:

```python
import json

with open("logs/interactions.jsonl") as f:
    logs = [json.loads(line) for line in f if line.strip()]

# Compare Q5 latency across phases
q5_logs = [l for l in logs if "sync-related" in l["query"]]
for log in q5_logs:
    print(f"{log['phase']:<20} {log['latency_ms']:>8}ms  "
          f"confidence:{log['confidence']}  {log['notes']}")
```

Output from your actual log (lines 5, 12, 55, 65, 71, 74):
```
phase2_baseline          0.0ms  confidence:None   (error — no ticket ID)
phase3_llm_v2         4085.7ms  confidence:0.8
phase4_rag           10651.3ms  confidence:0.0    retrieved:12 avg_rel:0.1438
phase4_rag            7752.9ms  confidence:0.0    retrieved:12 avg_rel:0.1438
phase4_rag            5423.4ms  confidence:0.9    retrieved:12 avg_rel:0.1438
phase4_rag            6995.8ms  confidence:0.9    retrieved:12 avg_rel:0.127
```

This single slice shows the full Q5 story: Phase 2 hard failure → Phase 3 working but shallow → Phase 4 deeper retrieval with improving confidence across successive runs.
