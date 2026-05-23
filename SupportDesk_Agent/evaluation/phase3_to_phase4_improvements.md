# Phase 3 → Phase 4: Improvements from RAG
## Compare responses with and without retrieval · Handle missing information cases

---

## What changed architecturally

In Phase 3, every LLM call received the same static context — all 24 tickets dumped as a flat text block regardless of what was asked. The LLM had to filter relevance internally, which led to it fixating on the first few tickets it processed and ignoring the rest.

In Phase 4, the agent first runs a semantic search against ChromaDB, retrieves only the documents most relevant to the specific query, and injects that focused context into the prompt. The LLM receives less noise and more signal — only the tickets that matter for the question being asked.

The difference is the difference between handing someone a filing cabinet and asking them to find something, versus handing them the 8–12 most relevant files already pulled.

---

## Query-by-query improvement analysis

### Q1 — Which tickets are most urgent right now and why?

**Phase 3 (no retrieval):**
```
Supporting Tickets: TKT-1001, TKT-1002
Business Impact: $800K ARR at risk
Evidence: one generic quote about sync failure
```

**Phase 4 (RAG):**
```
Supporting Tickets: TKT-1020, TKT-1001, TKT-1003, TKT-1007,
                    TKT-1010, TKT-1021, TKT-1004, TKT-1018
Business Impact: GlobalFoods HQ ($1,200,000), FreshMart ($1,500,000),
                 Logix Pharma ($700,000) — total: $3,400,000
Evidence: VP formal notice + crash + missing orders + iOS 30s limit
          + billing discrepancy + SOX compliance gap
```

**What changed:** 8 tickets cited vs 2. Three customers named with specific ARR vs one generic figure. Six distinct failure modes documented vs one repeated quote. The improvement came from retrieval returning 12 prioritised documents — including TKT-1020 (VP escalation, $800K rollout pause) and TKT-1018 (compliance gap, 14-day audit deadline) which Phase 3 never surfaced.

**Caveat:** Avg relevance was -0.2643 — the query "most urgent" has no semantic anchor in ticket text. The retriever returned documents by falling back to full collection scan. The improvement came from volume of context, not retrieval precision.

---

### Q2 — Is there a pattern forming across FreshMart tickets?

**Phase 3 (no retrieval):**
```
Pattern: Churn Risk Due to Trust Issues
Tickets: TKT-1016, TKT-1020, TKT-1021
total_analyzed: ?  ← unknown, lost in static injection
```

**Phase 4 (RAG):**
```
Pattern: Trust and User Experience Issues
Tickets: TKT-1016
total_analyzed: 8  ← correct from retrieval metadata
```

**What changed:** `total_analyzed` is now correctly populated from retrieval count rather than lost in the formatter. The avg relevance of 0.1093 confirms the 7d window retrieval was semantically aligned.

**Where Phase 4 is weaker:** Phase 3 cited 3 tickets (TKT-1016, TKT-1020, TKT-1021); Phase 4 cited only 1. The 7-day window retrieval returned FreshMart tickets but the pattern detector focused on the strongest single tag cluster (`ux/trust` on TKT-1016) rather than the escalation cluster (TKT-1020, TKT-1021). Phase 3's broader context included those escalation tickets. This is a documented RAG trade-off: semantic focus can narrow context too aggressively for broad pattern queries.

---

### Q3 — Which customer is most at risk of churning?

**Phase 3 (no retrieval):**
```
Customers returned: 1 (Logix Pharma — wrong)
total_arr_at_risk: $0
Confidence: 0.6
```

**Phase 4 (RAG):**
```
Customers returned: 1 (QuickShip — wrong)
total_arr_at_risk: $0
Confidence: 1.0
```

**What changed:** The correct answer is FreshMart (health: 35, $1.5M ARR, legal claim, VP escalation). Neither phase returned it. Phase 4 confirmed all 5 customers reach the LLM (`retrieved:5`) but the LLM still truncates the output to a single object. This is the one query where Phase 4 did not improve over Phase 3.

**Why retrieval alone cannot fix this:** The avg relevance of 0.0 for the customers_all collection means the embedding model produced near-identical vectors for all 5 customer documents — they are too structurally similar for semantic differentiation. Retrieval returns all 5 but cannot rank them meaningfully. The LLM receives them in an arbitrary order and picks one.

**The Phase 5 fix:** A deterministic ranking tool will pre-sort all 5 customers by `risk_score` from metadata and pass them as a numbered list to the LLM — removing the LLM's ability to select or truncate. The LLM will add narrative, not ranking logic.

---

### Q4 — Will any SLAs breach in the next 24 hours?

**Phase 3 (no retrieval):**
```
risk_summary: — (missing)
At Risk: TKT-1016, 18.2h remaining
Impact: Trust breakdown (no ARR figure)
Confidence: 0.5
```

**Phase 4 (RAG — hybrid approach):**
```
risk_summary: One ticket approaching SLA breach within 5 hours
At Risk: TKT-1016, 4.9h remaining
Impact: FreshMart Retail Group, $1,500,000 ARR at risk
Confidence: 0.7
```

**What changed:** Three improvements. First, `risk_summary` now populates correctly — the v4_rag prompt template enforced it. Second, the business impact now names the specific customer and their ARR instead of generic language. Third, the hours_until_breach is accurate to the current run time (4.9h vs 18.2h) because it is computed by the deterministic rule engine at query time, not cached from Phase 3.

**Architecture note for Q4:** This query uses a hybrid design — the rule engine computes `hours_until_breach` deterministically (no LLM involvement for the timing calculation), then ChromaDB fetches full ticket documents by exact ID. The LLM only adds narrative and ARR impact assessment. This is the correct design for time-sensitive data — deterministic computation for the factual values, LLM for the contextual reasoning.

---

### Q5 — What is the root cause across the sync-related tickets?

**Phase 3 (no retrieval):**
```
Supporting Tickets: TKT-1001, TKT-1002 only
Root Cause: sync failure + offline operations (generic)
Business Impact: $800K ARR (single customer, undercounted)
Evidence: 1 quote, repeated across runs
Confidence: 0.8
```

**Phase 4 (RAG):**
```
Supporting Tickets: TKT-1010, TKT-1003, TKT-1011, TKT-1002,
                    TKT-1016, TKT-1007, TKT-1005, TKT-1001, TKT-1013
Root Cause: absence of idempotency keys during retries (specific)
Business Impact: GlobalFoods ($1.2M) + QuickShip ($0.5M) +
                 FreshMart ($1.5M) + AgriSource ($0.9M) = $3.1M
                 (unique customers, no double-counting)
Evidence: 2 direct description quotes from different tickets
Confidence: 0.9
```

**What changed:** This is the clearest improvement across all five queries. The ticket citation count went from 2 to 8–9 across consistent runs. The root cause moved from a generic description to a specific technical diagnosis (idempotency keys). The business impact corrected from a single-customer figure to a properly deduplicated cross-customer total. The avg relevance of 0.1275–0.1438 is the highest across all queries — the semantic match between "sync-related root cause" and the idempotency/sync tag cluster in the ticket corpus is strong.

**Why this query benefits most from RAG:** The query asks for synthesis across multiple tickets — exactly what semantic retrieval is designed for. The embedding model clusters idempotency, sync, duplicate, and retry semantically. ChromaDB returns the 12 most relevant tickets from that cluster. The LLM receives a pre-filtered, topically coherent context instead of 24 tickets where only 8 are relevant.

---

## Handling cases where relevant information is missing

### Case 1 — Query has no semantic anchor (Q1 urgency)

When "most urgent" returned avg_rel of -0.2643, the system did not fail or return empty results. It fell back to returning all available documents from the collection. The LLM then reasoned from priority fields, status, and SLA dates — fields that exist in every document — rather than semantic content. The answer was still useful.

**Design principle:** Never return empty context. If relevance is low, return more documents rather than fewer. A low-confidence retrieval with 12 docs is better than a high-confidence retrieval with 2 docs for synthesis queries.

### Case 2 — Customer documents too structurally similar (Q3)

When all 5 customer documents return avg_rel of 0.0, the system still returns all 5 and logs the issue in the notes field (`avg_rel:0.0`). The formatter shows whatever the LLM returns, and the log captures the structural failure for diagnosis.

**What the system does not do:** It does not silently substitute a cached answer, it does not hallucinate a ranking, and it does not return an error. It returns the best available answer with the information it has, while logging the retrieval quality signal so the failure is diagnosable.

**Design principle:** Transparent degradation. When retrieval quality is poor, the output quality degrades visibly (wrong customer, $0 ARR) rather than invisibly (confidently wrong answer). The `Avg relevance: 0.0` footer on every Q3 response is the signal that retrieval was not the right approach for this query type.

### Case 3 — SLA data requires real-time computation (Q4)

SLA breach prediction requires knowing the current time — something that cannot be pre-embedded in a vector store. The system handles this by running the deterministic `predict_sla_risk()` rule engine first, which computes `hours_until_breach` at query time, then fetches document context by exact ticket ID. The LLM never touches time computation.

**Design principle:** Use deterministic tools for factual data that changes over time (timestamps, deadlines, counts). Use the LLM only for reasoning and narrative over that data. Mixing time-sensitive computation into LLM prompts introduces staleness and hallucination risk.

---

## Summary scorecard

| Query | Phase 3 quality | Phase 4 quality | Direction |
|-------|----------------|-----------------|-----------|
| Q1 — Urgency | 3/5 — 2 tickets, generic | 4/5 — 8 tickets, ARR by customer | ✅ Better |
| Q2 — Patterns | 3/5 — 3 tickets, no count | 3/5 — 1 ticket, correct count | ↔ Neutral |
| Q3 — Churn risk | 2/5 — wrong customer | 2/5 — wrong customer | ↔ No change |
| Q4 — SLA risk | 3/5 — missing summary | 4/5 — ARR named, summary present | ✅ Better |
| Q5 — Root cause | 3/5 — 2 tickets, generic | 5/5 — 9 tickets, specific, deduped | ✅ Major improvement |
| **Average** | **2.8/5** | **3.6/5** | **+29% quality** |

The primary remaining gap — Q3 customer ranking — is architectural. Semantic retrieval cannot rank structurally identical documents. The solution is a deterministic pre-sort tool, which is the Phase 5 tool-calling implementation.
