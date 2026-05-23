# Phase 2 — Baseline Agent Results

## Run date: 29 April 2026

## Test Query Results

| Query | Intent Detected | Tool Called | Latency (ms) | Grounded | Notes |
|-------|----------------|-------------|--------------|----------|-------|
| Q1 — most urgent tickets   | | | | | |
| Q2 — FreshMart patterns    | | | | | |
| Q3 — customer churn risk   | | | | | |
| Q4 — SLA breach next 24h   | | | | | |
| Q5 — sync root cause       | | | | | |

## Demonstrated Limitations

### Limitation 1 — No semantic understanding
Query: "What keeps going wrong with orders?"
Expected intent: detect_patterns
Actual output: detects patters across tickets based on tag-matching [sync,offline,duplicate,billing,churn-risk] fails on natural phrases.
Issue: Keyword router misses natural language — 
       only matches exact keywords like "pattern" or "recurring"

### Limitation 2 — No cross-ticket reasoning
Query: "What is the root cause across the sync-related tickets?"
Expected intent: Reasoning across multiple tickets to find common root cause
Actual output: ERROR: No ticket ID found in query. Please include a ticket ID like TKT-1002.
Issue: Returns generic tag-based response — 
        cannot synthesise reasoning across ticket descriptions

## Why this version is insufficient for real users
1. Intent detection fails on natural phrasing (no semantic understanding)
2. Root cause analysis is tag-matching only — no description reading
3. Responses are mechanical templates — not actionable narrative
4. Cannot reason across multiple tickets simultaneously
5. Confidence scores are hardcoded — not computed from evidence quality