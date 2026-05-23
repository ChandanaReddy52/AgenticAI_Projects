# Phase 3 — LLM Prompt Strategy Comparison
## Capstone: AI Support Intelligence Agent — GlobalFoods Inc.
**Run date:** 29 April 2026
**Model:** GPT-4o-mini | **Temperature:** 0.2 | **Max tokens:** 1500
**Strategies tested:** V1 (Direct) · V2 (Structured JSON) · V3 (Chain-of-Thought)

---

## 1. STRATEGY DEFINITIONS

| Strategy | Approach | Core Instruction |
|----------|----------|------------------|
| **V1 — Direct** | Simple natural language prompt. No format enforcement. | "Analyze this ticket and provide root cause and action." |
| **V2 — Structured JSON** | Explicit JSON schema with field names and types defined. Array wrapper enforced. | "Return ONLY this exact JSON: `{...}`" |
| **V3 — Chain-of-Thought** | Numbered reasoning steps before output. Forces visible thinking. | "Step 1: read title. Step 2: check tags. … Then output JSON." |

---

## 2. LATENCY COMPARISON (milliseconds)

| Query | V1 Direct | V2 Structured | V3 Chain-of-Thought | Fastest |
|-------|-----------|---------------|----------------------|---------|
| Q1 — Most urgent tickets | 5,155 | 4,401 | 9,871 | **V2** |
| Q2 — FreshMart patterns | 14,326 | 7,637 | 17,205 | **V2** |
| Q3 — Customer churn risk | 12,632 | 8,459 | 21,617 | **V2** |
| Q4 — SLA breach next 24h | 11,127 | 4,986 | 8,602 | **V2** |
| Q5 — Sync root cause | 4,402 | 3,982 | 12,272 | **V2** |
| **Average** | **9,528ms** | **5,893ms** | **13,913ms** | **V2** |
| **vs V2 baseline** | +61.7% slower | — | +136.1% slower | — |

**Finding:** V2 is fastest on every single query. V3 (Chain-of-Thought) is 2.4x slower than V2 on average. V1 is 1.6x slower than V2 despite being the simplest prompt — this is because V1 gives the model less structural constraint, causing it to generate more exploratory text before settling on an answer.

---

## 3. TOKEN USAGE COMPARISON

| Query | V1 Tokens | V2 Tokens | V3 Tokens |
|-------|-----------|-----------|-----------|
| Q1 | 2,397 | 2,413 | 2,537 |
| Q2 | 1,321 | 1,213 | 1,978 |
| Q3 | 925 | 1,286 | 1,826 |
| Q4 | 853 | 908 | 1,058 |
| Q5 | 2,395 | 2,412 | 2,584 |
| **Average** | **1,578** | **1,646** | **1,997** |

**Finding:** V2 and V1 use comparable tokens. V3 uses 27% more tokens than V2 on average due to the reasoning steps before the JSON output — these steps are useful for complex queries but add cost and latency on simple ones.

---

## 4. OUTPUT QUALITY COMPARISON — PER QUERY

### Quality scoring rubric
| Score | Meaning |
|-------|---------|
| 5 | Complete, specific, grounded in ticket data, actionable |
| 4 | Mostly complete, minor gaps in specificity or evidence |
| 3 | Partial — correct intent but missing key fields or vague |
| 2 | Structural failure — empty fields, parse issue, wrong schema |
| 1 | Complete failure — fallback message or crash |

---

### Q1 — "Which tickets are most urgent right now and why?"

| Dimension | V1 Direct | V2 Structured | V3 Chain-of-Thought |
|-----------|-----------|---------------|----------------------|
| Intent routed correctly | ✅ cross_ticket | ✅ cross_ticket | ✅ cross_ticket |
| Root cause identified | ✅ sync failure + offline ops | ✅ sync failure + data loss | ✅ sync failure + idempotency |
| Supporting tickets cited | TKT-1001, TKT-1002 | TKT-1001, TKT-1002 | TKT-1002, TKT-1020, TKT-1001, TKT-1003, TKT-1004 |
| Evidence grounded | ✅ exact quotes from tickets | ✅ exact quotes from tickets | ✅ ticket-specific evidence |
| Business impact | $800K ARR | $800K ARR | $800K ARR + $42K billing |
| Specificity | Moderate | Moderate | **High — names specific figures** |
| Confidence returned | 0.85 | 0.85 | **0.95** |
| **Quality score** | **4/5** | **4/5** | **5/5** |

**Winner Q1: V3** — cited 5 tickets with specific dollar figures per ticket. V1 and V2 cited only TKT-1001 and TKT-1002, missing the escalation ticket TKT-1020 ($800K rollout pause) and the billing ticket TKT-1004.

---

### Q2 — "Is there a pattern forming across FreshMart tickets?"

| Dimension | V1 Direct | V2 Structured | V3 Chain-of-Thought |
|-----------|-----------|---------------|----------------------|
| Intent routed correctly | ✅ detect_patterns | ✅ detect_patterns | ✅ detect_patterns |
| Pattern returned | ❌ 7 empty pattern objects | ✅ 1 pattern (churn risk) | ✅ 1 pattern (duplicate orders) |
| Tags identified | ❌ empty arrays | sync, offline, trust, churn-risk | sync, duplicate |
| Ticket IDs cited | ❌ none | TKT-1016, TKT-1020, TKT-1021 | TKT-1002, TKT-1004 |
| Trend analysis | ❌ missing | accelerating | stable |
| Root cause signal | ❌ missing | Trust breakdown increasing churn | Recurring duplicate order impact |
| Actionable recommendation | ❌ missing | Enhance UX to reduce churn risk | Review idempotency implementation |
| JSON compliance | ❌ schema drift — wrong field names | ✅ correct schema | ✅ correct schema |
| **Quality score** | **1/5** | **3/5** | **4/5** |

**Winner Q2: V3** — correctly identified the duplicate order pattern with specific ticket IDs and a concrete recommendation tied to idempotency. V2 identified the churn signal but missed the root technical cause. V1 completely failed — returned 7 empty pattern objects (LLM generated the container array but did not populate any fields).

**V1 failure note:** V1 JSON compliance failure on Q2. The LLM returned a different schema key (`recommendedActions` instead of `recommendation`, empty arrays for `tag_cluster`) — the `_ensure_list` wrapper caught the outer structure but the inner fields were all null. This triggered the `json_retry` flag in the logs (line 16 of interactions.jsonl).

---

### Q3 — "Which customer is most at risk of churning?"

| Dimension | V1 Direct | V2 Structured | V3 Chain-of-Thought |
|-----------|-----------|---------------|----------------------|
| Intent routed correctly | ✅ rank_customer_risk | ✅ rank_customer_risk | ✅ rank_customer_risk |
| Schema compliance | ❌ `churn_risk_ranking` key — parse issue | ✅ `ranked_customers` | ✅ `ranked_customers` |
| All 5 customers ranked | ❌ parse failure — 0 displayed | ❌ 1 customer only (AgriSource) | ❌ 1 customer only (AgriSource) |
| Highest risk customer correct | ❌ not shown | ❌ Wrong — AgriSource is LOW risk | ❌ Wrong — AgriSource is LOW risk |
| Expected top risk | FreshMart (health 35, $1.5M ARR, legal claim) | FreshMart (health 35, $1.5M ARR, legal claim) | FreshMart (health 35, $1.5M ARR, legal claim) |
| Total ARR at risk | ❌ $0 | ❌ $0 | ❌ $0 |
| Confidence | null | 0.6 | 0.75 |
| **Quality score** | **1/5** | **2/5** | **2/5** |

**All strategies failed Q3.** Root cause: the LLM consistently returned only the lowest-risk customer (AgriSource) instead of all 5. The prompt instruction "rank ALL customers — do not omit any" was not followed. V1 additionally returned the wrong schema key (`churn_risk_ranking` instead of `ranked_customers`), which caused a parse failure. This is the primary documented Phase 3 failure mode (see Section 6).

---

### Q4 — "Will any SLAs breach in the next 24 hours?"

| Dimension | V1 Direct | V2 Structured | V3 Chain-of-Thought |
|-----------|-----------|---------------|----------------------|
| Intent routed correctly | ✅ predict_sla_risk | ✅ predict_sla_risk | ✅ predict_sla_risk |
| Already breached identified | ✅ 6 tickets | ✅ 6 tickets | ✅ 6 tickets |
| At-risk tickets (TKT-1016) | ❌ not shown | ✅ TKT-1016, 18.2h, prob 0.7 | ✅ TKT-1016, 18.2h, prob 0.7 |
| ARR exposure quantified | ✅ mentioned in narrative ($1.2M + $3M) | ❌ not shown | ✅ $1.5M FreshMart |
| Risk summary sentence | ✅ clear narrative | ❌ missing (shows `—`) | ❌ missing (shows `—`) |
| Recommended action | ❌ not structured | ✅ "Assign within 2 hours" | ✅ "Assign within 2 hours with high urgency" |
| JSON compliance | ❌ `risk_summary` + `recommended_actions` keys — wrong names → json_retry | ✅ correct | ✅ correct |
| **Quality score** | **3/5** | **3/5** | **4/5** |

**Winner Q4: V3** — provided the most specific business impact ($1.5M FreshMart ARR) and an urgency-graded recommendation. V1 had the best narrative text but failed JSON schema compliance, requiring a retry. V2 returned the correct structure but missing the risk_summary and ARR exposure fields.

**Note:** The `risk_summary` field showing `—` in V2 and V3 is a formatter gap — the LLM returned it inside the `at_risk` array object rather than at the top level. The data is correct; the display is incomplete. This is a minor formatter issue, not an LLM reasoning failure.

---

### Q5 — "What is the root cause across the sync-related tickets?"

| Dimension | V1 Direct | V2 Structured | V3 Chain-of-Thought |
|-----------|-----------|---------------|----------------------|
| Intent routed correctly | ✅ cross_ticket | ✅ cross_ticket | ✅ cross_ticket |
| Root cause identified | ✅ Idempotency + sync failure | ✅ Idempotency + sync failure | ✅ Error handling + idempotency |
| Tickets cited | TKT-1001, TKT-1002 | TKT-1001, TKT-1002 | TKT-1001, TKT-1002, TKT-1003, TKT-1005, TKT-1010, TKT-1011, TKT-1013 |
| Evidence grounded | ✅ direct quotes from descriptions | ✅ direct quotes | ✅ ticket-specific evidence per ticket |
| Business impact | $800K ARR + churn risk | $800K ARR | Financial discrepancies + compliance |
| Specificity of fix | Idempotency key on POST | Idempotency key mechanism | Idempotency + error handling |
| **Phase 2 comparison** | ❌ Phase 2: ERROR — no ticket ID | ✅ Real analysis returned | ✅ Real analysis returned |
| V3 duplicate output issue | — | — | ⚠️ Response text repeated 8x |
| **Quality score** | **4/5** | **4/5** | **3/5** (penalised for duplication) |

**Winner Q5: V1 and V2 tied** — both produced clean, grounded cross-ticket analysis. V3 cited more tickets (7 vs 2) but its output was repeated 8 times in sequence, indicating a streaming/rendering loop in the formatter when the CoT reasoning section interleaved with the JSON block. This is the second documented Phase 3 failure mode.

**Phase 2 vs Phase 3 comparison — Q5:**
| Phase | Response |
|-------|---------|
| Phase 2 (baseline) | `ERROR: No ticket ID found in query. Please include a ticket ID like TKT-1002.` |
| Phase 3 V2 | Root Cause: Missing idempotency on POST /api/orders. Pattern: sync failures → data loss + duplicates. Tickets: TKT-1001, TKT-1002. Fix: Implement idempotency key mechanism. Confidence: 0.85 |

This is the single clearest demonstration of LLM improvement over the baseline. Q5 went from a hard error to a reasoned, grounded, evidence-backed answer.

---

## 5. AGGREGATE QUALITY SCORES

| Query | V1 Direct | V2 Structured | V3 Chain-of-Thought |
|-------|-----------|---------------|----------------------|
| Q1 — Most urgent tickets | 4/5 | 4/5 | **5/5** |
| Q2 — FreshMart patterns | 1/5 | 3/5 | **4/5** |
| Q3 — Customer churn risk | 1/5 | 2/5 | 2/5 |
| Q4 — SLA breach 24h | 3/5 | 3/5 | **4/5** |
| Q5 — Sync root cause | 4/5 | **4/5** | 3/5 |
| **Total / 25** | **13/25 (52%)** | **16/25 (64%)** | **18/25 (72%)** |
| **Avg latency** | 9,528ms | **5,893ms** | 13,913ms |
| **JSON compliance** | 2/5 pass | **5/5 pass** | 4/5 pass |
| **json_retry triggered** | 3/5 queries | 0/5 queries | 1/5 queries |

---

## 6. IMPROVEMENTS OVER PHASE 2 BASELINE

| Capability | Phase 2 (Baseline) | Phase 3 (LLM) | Improvement |
|------------|-------------------|---------------|-------------|
| Q5 cross-ticket reasoning | Hard error — no ticket ID | Grounded root cause analysis | ✅ Critical fix |
| Root cause identification | Tag matching only (4 patterns hardcoded) | Reads descriptions, infers causality | ✅ Qualitative leap |
| Evidence citation | Tags + priority field only | Direct quotes from ticket descriptions | ✅ Significant |
| Confidence scoring | Hardcoded (0.4 baseline) | Computed per-response (0.5–0.95) | ✅ Real signal |
| Business impact | None — rules had no ARR reasoning | $800K ARR linked to specific tickets | ✅ New capability |
| Pattern trend analysis | Count-based (accelerating if more high-priority in second half) | Semantic trend with LLM reasoning | ✅ Improved |
| Response narrative | Mechanical template — no context | Natural language grounded in data | ✅ Significant |
| Response latency | <5ms (rule-based) | 3,982–21,617ms (LLM) | ⚠️ New constraint |

---

## 7. NEW FAILURE MODES DISCOVERED IN PHASE 3

### Failure Mode 1 — LLM output schema drift (V1)
**Queries affected:** Q2, Q3, Q4
**Description:** V1's unstructured prompt allows the LLM to use its own field names instead of the specified schema. Q3 returned `churn_risk_ranking` instead of `ranked_customers`. Q4 returned `recommended_actions` (plural) instead of `recommended_action`. Q2 returned `recommendedActions` (camelCase). All triggered `json_retry` in the logs.
**Evidence:** interactions.jsonl lines 16, 19, 22 — all show `"json_retry": true` for V1 on Q2, Q3, Q4.
**Severity:** High — causes parse failure and empty display output.
**Fix applied:** Explicit field name enforcement in V2/V3 prompts. `_ensure_list()` added as fallback wrapper. Still fails when top-level key name is wrong.

### Failure Mode 2 — V3 response duplication loop (Q5)
**Queries affected:** Q5 V3 strategy
**Description:** Chain-of-thought responses contain a reasoning section followed by a JSON block. The JSON extractor in `call_llm()` uses `rfind("{")` to locate the last JSON object — but when the CoT reasoning text contains partial JSON fragments, the extractor picks up an intermediate fragment and the formatter iterates over a partially-parsed structure, repeating it multiple times.
**Evidence:** Terminal output for Q5 V3 shows the same paragraph block ("Supporting Tickets: TKT-1001, TKT-1002...") repeated 8 times.
**Severity:** Medium — correct data is present but unreadable. Logs show correct keys (`response_keys` contains all expected fields), so the underlying LLM response was valid.
**Fix for Phase 4:** Replace `rfind` with a proper JSON bracket-balancing extractor, or instruct CoT prompts to output `---JSON_START---` as a delimiter before the JSON block.

### Failure Mode 3 — Customer ranking truncation (Q3, all strategies)
**Queries affected:** Q3 — all three strategies
**Description:** The LLM consistently returned only 1 of 5 customers instead of all 5, despite the prompt instruction "Rank ALL 5 customers — do not omit any." The returned customer was the lowest-risk one (AgriSource), not the highest (FreshMart). This suggests the LLM is prioritizing the final item in the input list over the most critical.
**Evidence:** All three Q3 responses show `total_arr_at_risk: $0` and only 1 customer in `ranked_customers`.
**Severity:** High — this is the core use case for the tool. A ranking tool that returns 1 of 5 customers is not functional.
**Root cause hypothesis:** The customer list in the prompt is ordered by data insertion, not by risk. The LLM may be picking the last customer it processed and returning only that one. Possible prompt fix: explicitly number each customer and instruct "return exactly 5 entries numbered 1–5."
**Fix for Phase 4:** Add customer data to vector store — retrieve all 5 in a single semantic search, then inject them with explicit numbering.

### Failure Mode 4 — General summary routed to cross_ticket (Q1)
**Queries affected:** Q1 on all strategies
**Description:** "Which tickets are most urgent right now" triggers `general_summary` intent in the router, but `llm_agent.py` overrides it to `cross_ticket` because the query has no specific ticket ID. The cross-ticket response is reasonable but misses the urgency ranking the user actually asked for — it returns root cause analysis instead of a priority-ordered list of tickets.
**Evidence:** interactions.jsonl lines 8, 13, 14, 15 — all show `"intent": "cross_ticket"` with `"tool_called": "general_summary"` — the mismatch between intent and tool shows the routing override is working but the response type is wrong.
**Severity:** Low-medium — the answer is relevant but not precisely what was asked.
**Fix for Phase 5:** Add a dedicated `urgency_ranking` tool that returns tickets sorted by priority + SLA proximity + ARR weight.

---

## 8. SELECTED DEFAULT STRATEGY — JUSTIFICATION

### Selected: **V2 — Structured JSON**

| Criterion | V1 Direct | V2 Structured | V3 Chain-of-Thought | Weight |
|-----------|-----------|---------------|----------------------|--------|
| Output quality (avg) | 52% | 64% | 72% | 35% |
| JSON compliance rate | 2/5 (40%) | **5/5 (100%)** | 4/5 (80%) | 30% |
| Average latency | 9,528ms | **5,893ms** | 13,913ms | 20% |
| Token cost | 1,578 | 1,646 | 1,997 | 10% |
| Production reliability | Low | **High** | Medium | 5% |
| **Weighted score** | **48%** | **78%** | **71%** |

### Reasoning

**V2 is selected as the default strategy** for the following reasons grounded in actual run data:

1. **JSON compliance is 100%.** V1 triggered `json_retry` on 3 of 5 queries. V3 triggered it on 1. V2 returned valid, parseable JSON on every single call. In a production agent, parse failures cause user-facing errors. Zero retries = zero failures on structural compliance.

2. **Latency is 38% lower than V1 and 58% lower than V3.** The average V2 response is under 6 seconds. V3 averages nearly 14 seconds. For a support lead doing real-time triage, a 14-second wait per query is operationally unacceptable.

3. **Quality is meaningfully better than V1.** V1 scored 52% quality vs V2's 64% — a 23% relative improvement — primarily because V1's unstructured prompts allow schema drift that silently discards data.

4. **V3's quality advantage does not justify the cost.** V3 scored 72% quality — 8 percentage points above V2 — but at 2.4x the latency and 21% higher token cost. The Q5 duplication bug in V3 also introduces a reliability risk that would require additional engineering to fix before production use.

5. **V3 is reserved for complex multi-step queries.** The correct architectural decision is: V2 as default, V3 as an optional escalation for queries where the user explicitly requests deeper reasoning. This is implemented via the `--strategy v3` flag.

### V3 use cases where it should be preferred over V2
- Cross-ticket root cause queries on large ticket sets (>10 tickets)
- Go/no-go release recommendations requiring multi-factor reasoning
- Customer risk summaries that need to weigh multiple signals simultaneously

---

## 9. PHASE 3 SUMMARY

### What Phase 3 proved

1. **LLM reasoning is categorically superior to rule-based tools** for cross-source inference. Q5 went from a hard error in Phase 2 to a grounded, evidence-backed root cause analysis in Phase 3. This alone justifies the LLM integration.

2. **Prompt structure determines reliability more than prompt complexity.** V2's simple but explicit schema enforcement outperformed V1's natural language approach on reliability, and matched or exceeded V3's complex chain-of-thought on production-relevant metrics (latency, JSON compliance, retry rate).

3. **The LLM was generating correct responses throughout Phase 2 testing.** The earlier Phase 3 display failures were entirely in the formatting layer — `format_llm_response()` routed `cross_ticket` responses through the `detect_patterns` branch, discarding valid data. This is a documented engineering lesson: LLM response quality and display quality are independent failure points.

4. **Customer ranking remains unresolved.** Q3 failed across all three strategies. This is the primary open issue entering Phase 4 — RAG retrieval of the full customer dataset should fix the truncation problem by ensuring all 5 customers are always present in the context window with explicit indexing.

### Metrics summary
| Metric | Phase 2 Baseline | Phase 3 LLM (V2) | Improvement |
|--------|-----------------|------------------|-------------|
| Q5 cross-ticket | Hard error | Root cause + evidence | ✅ Fixed |
| Avg response quality | 2.4/5 (estimated) | 3.2/5 measured | +33% |
| JSON compliance | N/A (template output) | 100% (V2) | — |
| Evidence grounding | Tags only | Ticket description quotes | ✅ Significant |
| Customer ranking | Rule-based composite score | LLM semantic ranking | ⚠️ Partial — truncation issue |
| Response latency | <5ms | 5,893ms avg (V2) | ⚠️ New constraint — 1,179x increase |

---

## 10. OPEN ISSUES ENTERING PHASE 4 (RAG)

| # | Issue | Expected Phase 4 Fix |
|---|-------|----------------------|
| 1 | Customer ranking returns 1/5 customers | RAG retrieves all 5 with explicit indexing |
| 2 | `total_analyzed: ?` shown in pattern output | Inject ticket count from retrieval metadata |
| 3 | Q5 only cites 2 tickets (TKT-1001, TKT-1002) in V2 | RAG retrieves all relevant sync tickets, not just top-2 |
| 4 | Q3 ARR at risk always $0 | Fix ranking aggregation after full list retrieval |
| 5 | V3 duplication loop | Fix JSON extractor to use delimiter instead of `rfind` |
