"""
compare_prompts.py — Run all 5 test queries across 3 strategies
Run from project root: python evaluation/compare_prompts.py
"""

import os, sys, time, json

# Ensure project root is on path regardless of where you run from
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from agent.llm_agent import run_llm_agent

EVAL_QUERIES = [
    ("Q1", "Which tickets are most urgent right now and why?"),
    ("Q2", "Is there a pattern forming across FreshMart tickets?"),
    ("Q3", "Which customer is most at risk of churning?"),
    ("Q4", "Will any SLAs breach in the next 24 hours?"),
    ("Q5", "What is the root cause across the sync-related tickets?"),
]

STRATEGIES = ["v1", "v2", "v3"]

# Output file — always written to evaluation/ relative to project root
OUTPUT_DIR  = os.path.join(PROJECT_ROOT, "evaluation")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "phase3_raw_results.json")


def run_comparison():
    results = []

    print("\n" + "="*70)
    print("PHASE 3 — PROMPT STRATEGY COMPARISON")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Output file:  {OUTPUT_FILE}")
    print("="*70)

    for qid, query in EVAL_QUERIES:
        print(f"\n{'─'*70}")
        print(f"QUERY {qid}: {query}")
        print(f"{'─'*70}")

        query_results = {
            "query_id":   qid,
            "query":      query,
            "strategies": {}
        }

        for strategy in STRATEGIES:
            print(f"\n  → Strategy {strategy.upper()}:")
            t0       = time.time()
            response = run_llm_agent(query, strategy=strategy, verbose=False)
            elapsed  = round((time.time() - t0) * 1000)

            # Full response printed — not truncated
            print(response)
            print(f"  [Latency: {elapsed}ms]")

            query_results["strategies"][strategy] = {
                "response_full":    response,
                "response_preview": response[:300],
                "latency_ms":       elapsed
            }

        results.append(query_results)

    # Save — always to evaluation/ in project root
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print(f"Comparison complete.")
    print(f"Results saved to: {OUTPUT_FILE}")
    print("Fill evaluation/phase3_comparison.md with your observations.")
    print("="*70)


if __name__ == "__main__":
    run_comparison()