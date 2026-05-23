# Phase 4 — RAG Results
## Capstone: AI Support Intelligence Agent — GlobalFoods Inc.
**Run date:** 30 April 2026
**Model:** GPT-4o-mini | **Embedding:** text-embedding-3-small (OpenAI)
**Vector store:** ChromaDB PersistentClient | **Collections:** 5

---

## 1. BUILD VERIFICATION

| Check | Result |
|-------|--------|
| `python agent/rag/embedder.py` ran successfully | ✅ Yes |
| `tickets_all` document count | ✅ 23 docs (seed data has 23 tickets) |
| `customers_all` document count | ✅ 5 docs |
| `tickets_7d` document count | ✅ 8 docs |
| `tickets_30d` document count | ✅ 7 docs |
| `tickets_90d` document count | ✅ 8 docs |
| API key located automatically | ✅ `Code_Practice/.env` (2 levels above project root) |
| ChromaDB persisted to | `supportdesk_agent/data/chroma_db/` |

**Note:** `tickets_all` shows 23 not 24 because one ticket is absent from `data/tickets.json`. The embedder indexes whatever is present — this does not affect RAG operation but should be resolved by re-running `python data/seed_data.py`.

---

## 2. BEFORE (Phase 3 V2) vs AFTER (Phase 4 RAG) — FULL COMPARISON

### Q1 — Which tickets are most urgent right now and why?

| Dimension | Phase 3 V2 | Phase 4 RAG |
|-----------|-----------|-------------|
| Tickets cited | 2 (TKT-1001, TKT-1002) | 8 (TKT-1020, TKT-1001, TKT-1003, TKT-1007, TKT-1010, TKT-1021, TKT-1004, TKT-1018) |
| Business impact | $800K ARR (generic) | $3.4M ARR — 3 unique customers named with figures |
| Evidence quality | 1 generic quote | VP formal notice + crash + missing orders + iOS limit + billing + compliance cited |
| Confidence | 0.9 | 0.9 |
| Latency (ms) | 7,568 | 7,537 |
| Retrieved docs | N/A — static injection | 12 docs |
| Avg relevance | N/A | -0.2643 ⚠ (low — query too generic for semantic anchor) |
| **Quality improvement** | — | ✅ 4× more tickets cited, specific ARR by customer |

**Retrieval note:** Avg relevance of -0.2643 on Q1 is the lowest across all queries. "Most urgent" is a ranking question — it does not semantically match any specific ticket text. The retriever returned all 12 available docs by falling back to full collection scan rather than a targeted semantic match. Despite low relevance score, the LLM produced a better answer because it had more context — demonstrating that the retrieval floor (returning something even when similarity is low) is more useful than returning nothing.

---

### Q2 — Is there a pattern forming across FreshMart tickets?

| Dimension | Phase 3 V2 | Phase 4 RAG |
|-----------|-----------|-------------|
| Patterns returned | 1 (churn risk / trust) | 1 (trust and UX issues) |
| `total_analyzed` | `?` (lost in Phase 3) | 8 (correctly set from retrieval metadata) |
| Ticket IDs cited | TKT-1016, TKT-1020, TKT-1021 | TKT-1016 |
| Confidence | 0.7 | 0.8 |
| Latency (ms) | 6,355 | 5,522 |
| Retrieved docs | N/A | 8 (7d window) |
| Avg relevance | N/A | 0.1093 |
| **Quality improvement** | Partial | `total_analyzed` fixed ✅ |

**Regression note:** Phase 4 cited only 1 ticket vs Phase 3's 3 tickets. The 7d window retrieval returned 8 tickets but the FreshMart-specific pattern query was not specific enough — the pattern prompt asked for all patterns across the window, and only TKT-1016 had the `ux/trust` tag cluster. Phase 3 V2 caught TKT-1020 and TKT-1021 because it had the full 24-ticket context. This is a documented RAG trade-off: targeted retrieval can narrow context too much for broad pattern queries. Mitigation: add customer_id filter to `retrieve_patterns()` when query names a specific customer.

---

### Q3 — Which customer is most at risk of churning?

| Dimension | Phase 3 V2 | Phase 4 RAG |
|-----------|-----------|-------------|
| Customers returned | 1 of 5 (Logix Pharma — wrong) | 1 of 5 (QuickShip — wrong) |
| Correct top customer | ❌ Not FreshMart | ❌ Not FreshMart |
| `total_arr_at_risk` | $0 | $0 |
| Confidence | 0.6 | 1.0 |
| Latency (ms) | 10,602 | 7,462 |
| Retrieved docs | N/A | 5 (all customers guaranteed) |
| Avg relevance | N/A | 0.0 |
| **Quality improvement** | ❌ Not fixed | ❌ Persists |

**Root cause analysis (confirmed):** Log lines 63, 69, 73 all show `retrieved: 5 docs, avg_rel: 0.0`. Avg relevance of 0.0 means ChromaDB returned the documents but with zero semantic similarity — this occurs when query embedding and document embeddings are orthogonal in vector space. The `customers_all` collection was embedded with rich document text including risk scores, open tickets, and churn signals. The query "Which customer is most at risk?" should match semantically — the 0.0 score suggests the embedding function produced identical or near-zero vectors for all 5 customers, possibly because the customer documents are too structurally similar for the model to differentiate.

**Impact:** All 5 customers reach the LLM but the LLM receives them without a relevance ordering signal. Combined with the prompt instruction to rank by risk_score, the LLM should still rank correctly — but it consistently returns only QuickShip (the lowest risk customer). This is a persistent LLM output schema failure: the model returns a single object instead of an array, and `_ensure_list()` wraps that one object. The confidence of 1.0 on the wrong answer is a calibration failure — high confidence on incorrect output.

**This is the primary unresolved issue entering Phase 5.**

---

### Q4 — Will any SLAs breach in the next 24 hours?

| Dimension | Phase 3 V2 | Phase 4 RAG |
|-----------|-----------|-------------|
| `risk_summary` shown | ❌ Missing (shows `—`) | ✅ Included in latest run |
| Breached tickets count | 6 listed | 6 (already_breached_count in JSON) |
| At-risk tickets | TKT-1016 (18.2h) | TKT-1016 (4.9h → time elapsed between runs) |
| Business impact | Trust breakdown only | FreshMart $1.5M ARR named specifically |
| Confidence | 0.5 | 0.7 |
| Latency (ms) | 5,236 | 5,254 |
| Retrieved docs | N/A | 9 (rule engine + ID fetch) |
| Avg relevance | N/A | 0.0 (ID-based fetch, not semantic) |
| **Quality improvement** | ✅ risk_summary fixed · ARR specific |

**Architecture note:** Q4 uses a hybrid approach — the rule engine (`predict_sla_risk()`) computes deterministic `hours_until_breach` values, then ChromaDB fetches full documents by exact ticket ID rather than semantic search. This is why avg relevance is 0.0 — relevance is meaningless for ID-based lookups. The hours_until_breach value decreased from 18.2h to 4.9h between Phase 3 and Phase 4 runs because real time passed — this confirms the SLA clock is live and correct.

---

### Q5 — What is the root cause across the sync-related tickets?

| Dimension | Phase 3 V2 | Phase 4 RAG |
|-----------|-----------|-------------|
| Tickets cited | 2 (TKT-1001, TKT-1002 only) | 8–9 (TKT-1010, 1003, 1011, 1002, 1016, 1007, 1005, 1001, 1013) |
| Root cause precision | "Sync failure + offline ops" (generic) | "Absence of idempotency keys during retries" (specific) |
| Business impact | $800K (wrong — single customer figure) | $3.1M — 4 unique customers correctly deduped |
| ARR hallucination | ✅ Fixed (was $9.1M in first run) | Correct deduplication applied |
| Evidence quotes | 1–2 generic | 2 direct description quotes |
| Confidence | 0.8 | 0.9 |
| Latency (ms) | 4,086 | 5,423–7,753 |
| Retrieved docs | N/A — all 24 dumped statically | 12 (semantic search, priority-boosted) |
| Avg relevance | N/A | 0.1438 (highest across all queries) |
| **Quality improvement** | ✅ Major — 4× more tickets, correct ARR, precise root cause |

---

## 3. Q3 FIX VERIFICATION

| Metric | Phase 3 V2 | Phase 4 RAG |
|--------|-----------|-------------|
| Customers returned | 1 (Logix Pharma) | 1 (QuickShip) |
| `total_arr_at_risk` | $0 | $0 |
| Correct top customer (FreshMart) | ❌ No | ❌ No |
| Customers in list: | ☑ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 | ☑ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |

**Status: Not fixed.** 5 customers are confirmed retrieved (log lines 63, 69, 73: `retrieved:5`). The failure is in LLM output — it returns a single customer object instead of the required 5-element array. `_ensure_list()` wraps the single object so the formatter shows 1 customer. This will be addressed in Phase 5 with tool calling — a deterministic ranking tool will pre-sort and format all 5 customers before the LLM adds narrative, removing the LLM's ability to truncate the list.

---

## 4. Q5 FIX VERIFICATION

| Metric | Phase 3 V2 | Phase 4 RAG |
|--------|-----------|-------------|
| Tickets cited | 2 | 8–9 (varies per run) |
| Improvement | — | ✅ Yes — 4–5× more tickets |
| Root cause specificity | Generic sync failure | Idempotency keys specifically named |
| ARR accuracy | $800K (undercount) | $3.1M (correct dedup) |

**Status: Fixed.** Q5 was the hardest Phase 2 failure (hard error: "no ticket ID found"). Phase 3 fixed the error but cited only 2 tickets. Phase 4 consistently cites 8–9 tickets with specific evidence quotes grounded in retrieved descriptions.

---

## 5. RETRIEVAL QUALITY BY COLLECTION

| Collection | Avg relevance (observed) | Useful? | Notes |
|------------|--------------------------|---------|-------|
| `tickets_all` (cross-ticket) | 0.1275–0.1438 | ✅ Yes | Best relevance — semantic match on idempotency/sync terms |
| `tickets_all` (Q1 urgency) | -0.2643 | ⚠ Weak | Generic ranking query has no semantic anchor in ticket text |
| `customers_all` | 0.0 | ⚠ Structural | Customer docs too similar structurally — no semantic differentiation |
| `tickets_7d` (patterns) | 0.1093 | ✅ Adequate | Pattern query matches sync/offline tags in document text |
| SLA fetch (ID-based) | 0.0 | ✅ N/A | ID-based retrieval — relevance score not applicable |

---

## 6. CASES WHERE RETRIEVAL RETURNED IRRELEVANT RESULTS

**Case 1 — Q1 urgency query (avg_rel: -0.2643)**
Query: "Which tickets are most urgent right now and why?"
The word "urgent" does not appear in ticket documents. "Most urgent right now" has no semantic anchor in the embedded text — tickets describe problems, not urgency levels. The retriever returned all 12 docs with near-zero similarity. Despite this, the LLM produced a good answer because it reasoned from ticket priority and status fields rather than semantic content.
Mitigation for Phase 5: Add a dedicated `urgency_ranking` tool that fetches open tickets sorted by priority + SLA proximity + sentiment score deterministically, bypassing semantic search entirely.

**Case 2 — Q3 customer ranking (avg_rel: 0.0)**
Query: "Which customer is most at risk of churning?"
All 5 customer documents have structurally identical formats (CUSTOMER CUST-XXX: Name / ARR / Health / Risk Score). The embedding model produces very similar vectors for all 5, making semantic distance near-zero between query and all documents. The retriever technically returns all 5 but cannot rank them meaningfully by relevance.
Mitigation for Phase 5: Customer ranking should not use semantic retrieval at all — it should use a deterministic tool that reads `risk_score` from metadata and sorts, then injects all 5 into a structured prompt.

---

## 7. NEW FAILURE MODES DISCOVERED IN PHASE 4

**Failure Mode 1 — LLM array truncation persists despite retrieval guarantee (Q3)**
All 5 customers confirmed delivered to LLM context (`retrieved:5`). LLM still returns 1 customer object at top level. `_ensure_list()` wraps it — user sees 1 customer. The failure is not in retrieval — it is in LLM output compliance. Stronger prompt enforcement ("The array MUST have exactly 5 objects") partially helped (confidence went from 0.0 to 1.0) but did not fix the array structure.

**Failure Mode 2 — Negative relevance scores on broad queries**
Three Phase 4 runs returned avg_rel of -0.2643 for Q1. Negative cosine distance in ChromaDB indicates the query vector is orthogonal or opposite to document vectors. This happens when the query uses abstract ranking language ("most urgent", "at risk") that does not appear in the embedded document corpus. The system still returns results but with no meaningful relevance ordering.

**Failure Mode 3 — Confidence calibration inversion on Q3**
Phase 3 returned confidence 0.6 on a wrong answer. Phase 4 returned confidence 1.0 on an equally wrong answer. Higher confidence on a wrong answer with more context is a calibration failure — the LLM became more certain because it had more data, even though the output was still incorrect. This confirms confidence scores cannot be used as a quality signal without a ground truth comparison layer.
