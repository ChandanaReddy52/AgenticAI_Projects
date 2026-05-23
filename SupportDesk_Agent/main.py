"""
main.py — CLI entry point for SupportDesk Agent

Phases:
  2 = Baseline rule-based      (agent/baseline_agent.py)
  3 = LLM + prompt strategies  (agent/llm_agent.py)
  4 = RAG + ChromaDB           (agent/rag_agent.py)
  5 = LangChain tool calling   (agent/langchain_agent.py)


Usage:
  python main.py                                   Phase 2 interactive
  python main.py --phase 3                         Phase 3 interactive (v2)
  python main.py --phase 3 --strategy v3           Phase 3 CoT
  python main.py --phase 4                         Phase 4 RAG interactive
  python main.py --run-eval                        Phase 2 evaluation
  python main.py --run-eval --phase 3              Phase 3 evaluation
  python main.py --run-eval --phase 4              Phase 4 RAG evaluation
  python main.py --compare                         Phase 3 V1/V2/V3 comparison
  python main.py --query "..." --phase 4
  python main.py --run-eval --phase 5        Phase 5 all 5 queries
  python main.py --run-eval --phase 6        Phase 6 all 5 queries
  python main.py --run-eval --phase 7        Phase 7 all 5 queries
  python main.py --run-eval --phase 8        Phase 8 all 5 queries
"""

import argparse, time

from agent.baseline_agent import run_agent
from agent.llm_agent      import run_llm_agent
from agent.rag_agent      import run_rag_agent
from agent.langchain_agent import run_langchain_agent
from agent.memory_agent import (run_memory_agent, init_session, reset_short_term_memory)
from agent.adaptive_agent import (run_adaptive_agent,  init_adaptive_session, record_feedback, run_before_after_demo)
from agent.adaptive_agent import run_with_graceful_fallback

# Never change these — same queries across all phases for comparison
EVAL_QUERIES = [
    "Q1: Which tickets are most urgent right now and why?",
    "Q2: Is there a pattern forming across FreshMart tickets?",
    "Q3: Which customer is most at risk of churning?",
    "Q4: Will any SLAs breach in the next 24 hours?",
    "Q5: What is the root cause across the sync-related tickets?"
]

# Commands that exit interactive mode
EXIT_COMMANDS = {"quit", "exit", "q", "bye", "stop"}


# ── Evaluation runners ────────────────────────────────────────────

def run_evaluation():
    print("\n" + "="*60)
    print("PHASE 2 EVALUATION — BASELINE (rule-based)")
    print("="*60)
    for q in EVAL_QUERIES:
        print(f"\n{'─'*60}\nQUERY: {q}\n{'─'*60}")
        print(run_agent(q, verbose=True))
    print("\n" + "="*60)
    print("Done. Check logs/interactions.jsonl")
    print("="*60)


def run_llm_evaluation(strategy: str = "v2"):
    print(f"\n{'='*60}")
    print(f"PHASE 3 EVALUATION — LLM | Strategy: {strategy.upper()}")
    print(f"{'='*60}")
    for q in EVAL_QUERIES:
        print(f"\n{'─'*60}\nQUERY: {q}\n{'─'*60}")
        print(run_llm_agent(q, strategy=strategy, verbose=True))
    print("\n" + "="*60)
    print(f"Done — strategy {strategy.upper()}. Check logs/interactions.jsonl")
    print("="*60)


def run_rag_evaluation():
    print(f"\n{'='*60}")
    print("PHASE 4 EVALUATION — RAG (ChromaDB + Embeddings)")
    print(f"{'='*60}")
    for q in EVAL_QUERIES:
        print(f"\n{'─'*60}\nQUERY: {q}\n{'─'*60}")
        print(run_rag_agent(q, verbose=True))
    print("\n" + "="*60)
    print("Done. Check logs/interactions.jsonl")
    print("="*60)

def run_langchain_evaluation():
    print(f"\n{'='*60}")
    print("PHASE 5 EVALUATION — LangChain Tool Calling")
    print(f"{'='*60}")
    for q in EVAL_QUERIES:
        print(f"\n{'─'*60}\nQUERY: {q}\n{'─'*60}")
        print(run_langchain_agent(q, verbose=True))
    print("\n" + "="*60)
    print("Done. Check logs/interactions.jsonl")
    print("="*60)

def run_memory_evaluation():
    print(f"\n{'='*60}")
    print("PHASE 6 EVALUATION — Memory Agent")
    print(f"{'='*60}")
    init_session()   # fresh session for eval
    for q in EVAL_QUERIES:
        print(f"\n{'─'*60}\nQUERY: {q}\n{'─'*60}")
        print(run_memory_agent(q, verbose=True))
    print("\n" + "="*60)
    print("Done. Check logs/interactions.jsonl")
    print("="*60)

def run_adaptive_evaluation():
    print(f"\n{'='*60}")
    print("PHASE 7 EVALUATION — Adaptive Agent")
    print(f"{'='*60}")
    init_adaptive_session()
    for q in EVAL_QUERIES:
        print(f"\n{'─'*60}\nQUERY: {q}\n{'─'*60}")
        print(run_adaptive_agent(q, verbose=True))
    print("\n" + "="*60)
    print("Done. Check logs/interactions.jsonl")
    print("="*60)

def run_deployment_eval():
    """Phase 8 evaluation — runs with graceful fallback + health check."""
    from deployment.health_check import run_health_check
    if not run_health_check(include_llm_ping=False):
        print("Health check failed — aborting eval")
        return
    print(f"\n{'='*60}")
    print("PHASE 8 EVALUATION — Deployment Readiness")
    print(f"{'='*60}")
    from agent.adaptive_agent import init_adaptive_session
    init_adaptive_session()
    for q in EVAL_QUERIES:
        print(f"\n{'─'*60}\nQUERY: {q}\n{'─'*60}")
        print(run_with_graceful_fallback(q, verbose=True))
    # Print latency stats
    from agent.logger import get_latency_stats, get_error_count
    stats  = get_latency_stats(phase_filter="phase8")
    errors = get_error_count(phase_filter="phase8")
    print(f"\n{'='*60}")
    print(f"Latency stats (phase8):")
    for tool, s in stats.items():
        print(f"  {tool:<30} avg:{s['avg_ms']}ms  "
              f"p95:{s['p95_ms']}ms  count:{s['count']}")
    print(f"Errors logged: {errors}")
    print(f"{'='*60}")

def demonstrate_graceful_failure():
    """Demonstrate fallback chain by forcing each level to fail."""
    print(f"\n{'='*60}")
    print("PHASE 8 — GRACEFUL FAILURE DEMONSTRATION")
    print(f"{'='*60}")
    query = "Which customer is most at risk of churning?"
    print(f"\nRunning with full fallback chain: {query}")
    result = run_with_graceful_fallback(query, verbose=True)
    print(f"\nFinal result:\n{result}")

# ── Prompt comparison — Phase 3 ───────────────────────────────────

def run_comparison():
    import json, os
    OUTPUT_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "evaluation", "phase3_raw_results.json"
    )
    results = []
    print("\n" + "="*70)
    print("PHASE 3 — PROMPT STRATEGY COMPARISON (V1 vs V2 vs V3)")
    print(f"Output: {OUTPUT_FILE}")
    print("="*70)

    for q in EVAL_QUERIES:
        print(f"\n{'─'*70}\nQUERY: {q}\n{'─'*70}")
        qr = {"query": q, "strategies": {}}
        for s in ["v1", "v2", "v3"]:
            print(f"\n  ── Strategy {s.upper()} ──")
            t0  = time.time()
            res = run_llm_agent(q, strategy=s, verbose=False)
            ms  = round((time.time()-t0)*1000)
            print(res)
            print(f"  [Latency: {ms}ms]")
            qr["strategies"][s] = {"response_full": res, "latency_ms": ms}
        results.append(qr)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print(f"Saved: {OUTPUT_FILE}")
    print("="*70)


# ── Phase 3 vs Phase 4 side-by-side comparison ────────────────────

def compare_phase3_vs_phase4(query: str, strategy: str = "v2"):
    """Run one query through Phase 3 and Phase 4 and print side by side."""
    print(f"\n{'='*70}")
    print(f"PHASE 3 vs PHASE 4 COMPARISON")
    print(f"Query: {query}")
    print(f"{'='*70}")

    print(f"\n── Phase 3 (LLM {strategy.upper()}) ──")
    t0   = time.time()
    p3   = run_llm_agent(query, strategy=strategy, verbose=False)
    ms3  = round((time.time()-t0)*1000)
    print(p3)
    print(f"[Phase 3 latency: {ms3}ms]")

    print(f"\n── Phase 4 (RAG) ──")
    t0   = time.time()
    p4   = run_rag_agent(query, verbose=False)
    ms4  = round((time.time()-t0)*1000)
    print(p4)
    print(f"[Phase 4 latency: {ms4}ms]")

    print(f"\n{'='*70}")
    print(f"Latency: Phase3={ms3}ms | Phase4={ms4}ms")
    print(f"{'='*70}")


# ── Interactive mode ──────────────────────────────────────────────

def interactive_mode(phase: str = "2", strategy: str = "v2"):
    """
    Phase-aware interactive mode.

    Built-in commands:
      quit / exit / q  → exit (all variants work)
      eval             → run 5 fixed queries for current phase
      compare          → Phase3 only: one query across V1/V2/V3
      compare4         → compare Phase3 vs Phase4 on one query
      phase            → show active phase
      help             → show all commands

    Note: you CANNOT switch phases by typing a command inside interactive mode.
    To switch phases: exit (type 'quit'), then run:
      python main.py --phase 3    or    python main.py --phase 4
    """
    labels = {
        "2": "Phase 2 — Baseline (rule-based)",
        "3": f"Phase 3 — LLM [{strategy.upper()}]",
        "4": "Phase 4 — RAG (ChromaDB)",
        "5": "Phase 5 — LangChain Tool Calling",
        "6": "Phase 6 — Memory Agent",
        "7": "Phase 7 — Adaptive Agent",
        "8": "Phase 8 — Deployment-Readiness"
    }
    label = labels.get(phase, f"Phase {phase}")

    print(f"\nSupportDesk Agent — {label}")
    print("Commands: quit | exit | eval | compare | compare4 | phase | help")
    print("To switch phases: type 'quit', then run main.py --phase X")
    print()

    while True:
        try:
            raw   = input("You: ").strip()
            query = raw.lower()

            if not raw:
                continue

            # ── Exit — all common variants ─────────────────────────
            if query in EXIT_COMMANDS:
                print("Exiting SupportDesk Agent.")
                break

            # ── Help ───────────────────────────────────────────────
            if query == "help":
                print(
                    "\nAvailable commands:\n"
                    "  quit / exit / q  → exit the agent\n"
                    "  eval             → run all 5 fixed queries\n"
                    "  compare          → (Phase 3) one query across V1/V2/V3\n"
                    "  compare4         → Phase 3 vs Phase 4 on one query\n"
                    "  phase            → show active phase\n"
                    "  help             → this message\n"
                    "\nTo switch phases: type 'quit', then:\n"
                    "  python main.py --phase 2  (baseline)\n"
                    "  python main.py --phase 3  (LLM)\n"
                    "  python main.py --phase 4  (RAG)\n"
                )
                continue

            # ── Phase info ─────────────────────────────────────────
            if query == "phase":
                print(f"\nActive: {label}\n")
                continue

            # ── Eval ───────────────────────────────────────────────
            if query == "eval":
                if phase == "4":   run_rag_evaluation()
                elif phase == "3": run_llm_evaluation(strategy)
                elif phase == "5": run_langchain_evaluation()
                elif phase == "6": run_memory_evaluation()
                elif phase == "7": run_adaptive_evaluation()
                elif phase == "8": run_deployment_eval()
                else:              run_evaluation()
                continue

            # ── Compare V1/V2/V3 — Phase 3 only ───────────────────
            if query == "compare":
                if phase != "3":
                    print(
                        "Compare (V1/V2/V3) only available in Phase 3.\n"
                        "Type 'quit' then run: python main.py --phase 3"
                    )
                    continue
                user_q = input("Query to compare across V1/V2/V3: ").strip()
                if user_q:
                    for s in ["v1", "v2", "v3"]:
                        print(f"\n── Strategy {s.upper()} ──")
                        t0 = time.time()
                        print(run_llm_agent(user_q, strategy=s, verbose=False))
                        print(f"[{round((time.time()-t0)*1000)}ms]")
                continue

            # ── Compare Phase 3 vs Phase 4 ─────────────────────────
            if query == "compare4":
                user_q = input("Query to compare Phase3 vs Phase4: ").strip()
                if user_q:
                    compare_phase3_vs_phase4(user_q, strategy=strategy)
                continue

            # ── Memory management commands — Phase 6 only ───────────────
            if query == "reset memory":
                print(reset_short_term_memory())
                continue

            if query == "show memory":
                from agent.memory_store import load_long_term_memory, build_memory_context
                lt = load_long_term_memory()
                print(f"\nSession count: {lt['session_count']}")
                print(f"Escalations logged: {len(lt['escalations'])}")
                print(f"Resolved patterns: {len(lt['resolved_patterns'])}")
                print(f"Customer notes: {sum(len(v) for v in lt['customer_notes'].values())}")
                print(f"\n{build_memory_context(lt)}\n")
                continue

            if query.startswith("note:"):
                # User manually adds a customer note
                # Format: "note: CUST-002 August renewal at risk"
                from agent.memory_store import (load_long_term_memory,
                                                add_customer_note)
                parts  = query[5:].strip().split(" ", 1)
                if len(parts) == 2:
                    cid, note = parts
                    lt = load_long_term_memory()
                    add_customer_note(lt, cid.upper(), note)
                    print(f"Note saved for {cid.upper()}: {note}")
                continue

            if query.startswith("feedback:"):
                parts = query[9:].strip().split(" ", 1)
                if parts and parts[0].isdigit():
                    rating = int(parts[0])
                    note   = parts[1] if len(parts) > 1 else ""
                    print(record_feedback(rating, note))
                continue

            if query == "show feedback":
                from agent.memory_store import (load_long_term_memory,
                                                get_feedback_summary)
                summary = get_feedback_summary(load_long_term_memory())
                print(f"\nFeedback summary:")
                print(f"  Total ratings:     {summary['total_feedback']}")
                print(f"  Average rating:    {summary['avg_rating']}/5")
                print(f"  Depth preference:  {summary['depth_preference']}")
                print(f"  Common complaints: {summary['common_complaints']}\n")
                continue

            if query == "demo adaptive":
                run_before_after_demo(
                    "Is there a pattern forming across FreshMart tickets?",
                    low_rating=2,
                    low_note="too brief, missing ticket details",
                    verbose=True
                )
                continue

            # ── Main agent routing ─────────────────────────────────
            if phase == "8":
                response = run_with_graceful_fallback(raw, verbose=True)
            elif phase == "7":
                response = run_adaptive_agent(raw, verbose=True)
            elif phase == "6":
                response = run_memory_agent(raw, verbose=True)
            elif phase == "5":
                response = run_langchain_agent(raw, verbose=True)
            elif phase == "4":
                response = run_rag_agent(raw, verbose=True)
            elif phase == "3":
                response = run_llm_agent(raw, strategy=strategy, verbose=True)
            else:
                response = run_agent(raw, verbose=True)

            print(f"\nAgent:\n{response}\n")

        except KeyboardInterrupt:
            print("\nExiting (Ctrl+C).")
            break


# ── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SupportDesk AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            python main.py                              Phase 2 interactive
            python main.py --phase 3                   Phase 3 LLM (v2 default)
            python main.py --phase 3 --strategy v3     Phase 3 CoT
            python main.py --phase 4                   Phase 4 RAG
            python main.py --run-eval --phase 4        Phase 4 all 5 queries
            python main.py --compare                   Phase 3 V1/V2/V3
            python main.py --query "sync root cause" --phase 4
            python main.py --run-eval --phase 5        Phase 5 all 5 queries
            python main.py --run-eval --phase 6        Phase 6 all 5 queries
            python main.py --run-eval --phase 7        Phase 7 all 5 queries
            python main.py --run-eval --phase 8        Phase 8 all 5 queries
                    """
    )
    parser.add_argument("--query",    type=str,  help="Single query mode")
    parser.add_argument("--run-eval", action="store_true",
                        help="Run all 5 fixed evaluation queries")
    parser.add_argument("--compare",  action="store_true",
                        help="Phase 3: compare V1/V2/V3 across all 5 queries")
    parser.add_argument("--phase",    type=str, default="2",
                        choices=["2","3","4","5","6","7", "8"],
                        help="Agent phase (default: 2)")
    parser.add_argument("--strategy", type=str, default="v2",
                        choices=["v1","v2","v3"],
                        help="Prompt strategy for Phase 3 (default: v2)")
    args = parser.parse_args()

    if args.compare:
        run_comparison()

    elif args.run_eval:
        if args.phase == "8": run_deployment_eval()
        elif args.phase == "7": run_adaptive_evaluation()
        elif args.phase == "6": run_memory_evaluation()
        elif args.phase == "5": run_langchain_evaluation()
        elif args.phase == "4": run_rag_evaluation()
        elif args.phase == "3": run_llm_evaluation(strategy=args.strategy)
        else:                   run_evaluation()

    elif args.query:
        if args.phase == "8": print(run_with_graceful_fallback(args.query, verbose=True))
        elif args.phase == "7": print(run_adaptive_agent(args.query, verbose=True))
        elif args.phase == "6": print(run_memory_agent(args.query, verbose=True))
        elif args.phase == "5": print(run_langchain_agent(args.query, verbose=True))
        elif args.phase == "4": print(run_rag_agent(args.query, verbose=True))
        elif args.phase == "3": print(run_llm_agent(args.query,
                                      strategy=args.strategy, verbose=True))
        else:                   print(run_agent(args.query, verbose=True))

    else:
        interactive_mode(phase=args.phase, strategy=args.strategy)
