"""
health_check.py — Startup validation before accepting any queries
Location: supportdesk_agent/deployment/health_check.py

FIX: loads .env by walking up directory tree before any check runs.
     Same pattern used by embedder.py and retriever.py.

Run standalone: python deployment/health_check.py
Called automatically by main.py on --phase 8 startup.
"""

import os, sys, json, time

# ── Path resolution ───────────────────────────────────────────────
# health_check.py is at: supportdesk_agent/deployment/health_check.py
# dirname once  → deployment/
# dirname twice → supportdesk_agent/   ← PROJECT_ROOT
__file__abs  = os.path.abspath(__file__)
DEPLOY_DIR   = os.path.dirname(__file__abs)
PROJECT_ROOT = os.path.dirname(DEPLOY_DIR)

# Add project root to path so deployment.config resolves
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Load .env by walking UP the directory tree ────────────────────
# This is the same pattern used by embedder.py and retriever.py.
# Works regardless of where .env lives (project root, Code_Practice/, etc.)

def _find_and_load_env(start: str) -> str | None:
    """Walk up directory tree until .env is found, then load it."""
    current = start
    for _ in range(8):                         # search up to 8 levels
        candidate = os.path.join(current, ".env")
        if os.path.isfile(candidate):
            try:
                from dotenv import load_dotenv
                load_dotenv(candidate, override=False)  # don't override if already set
                return candidate
            except ImportError:
                # dotenv not installed — parse manually
                with open(candidate) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, val = line.partition("=")
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = val
                return candidate
        parent = os.path.dirname(current)
        if parent == current:                  # reached filesystem root
            break
        current = parent
    return None

# Load .env BEFORE importing config (config reads os.getenv at import time)
_env_path = _find_and_load_env(PROJECT_ROOT)

# ── Now import config (API key is in env by this point) ───────────
from deployment.config import CONFIG


# ── Health check functions ────────────────────────────────────────

def check_env() -> tuple[bool, str]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        # Show where we searched so user knows what to fix
        search_path = PROJECT_ROOT
        searched    = []
        current     = PROJECT_ROOT
        for _ in range(8):
            searched.append(current)
            parent = os.path.dirname(current)
            if parent == current: break
            current = parent
        return False, (
            "OPENAI_API_KEY not set\n"
            f"  .env file searched in:\n"
            + "\n".join(f"    {p}" for p in searched[:5])
            + "\n  Create a .env file in any of the above with:\n"
              "    OPENAI_API_KEY=sk-your-key-here"
        )
    if not key.startswith("sk-"):
        return False, (
            f"OPENAI_API_KEY format invalid (got: {key[:12]}...)\n"
            "  Expected format: sk-..."
        )
    env_note = f" (loaded from {_env_path})" if _env_path else " (from system env)"
    return True, f"API key present ({key[:8]}...){env_note}"


def check_data_files() -> tuple[bool, str]:
    results = []
    all_ok  = True
    for name, path in [
        ("tickets.json",   CONFIG.tickets_file),
        ("customers.json", CONFIG.customers_file),
    ]:
        if not os.path.exists(path):
            results.append(f"  ✗ {name} — NOT FOUND at {path}")
            all_ok = False
        else:
            try:
                with open(path) as f:
                    data = json.load(f)
                count = len(data) if isinstance(data, list) else 1
                results.append(f"  ✓ {name} — {count} records")
            except json.JSONDecodeError as e:
                results.append(f"  ✗ {name} — JSON parse error: {e}")
                all_ok = False
    return all_ok, "\n".join(results)


def check_chromadb() -> tuple[bool, str]:
    if not os.path.isdir(CONFIG.chroma_dir):
        return False, (
            f"  ✗ ChromaDB not found at {CONFIG.chroma_dir}\n"
            "    Run: python agent/rag/embedder.py"
        )
    try:
        import chromadb
        client      = chromadb.PersistentClient(path=CONFIG.chroma_dir)
        collections = client.list_collections()
        names       = [c.name for c in collections]
        results     = []
        required    = ["tickets_all", "customers_all"]
        all_ok      = True

        for req in required:
            if req not in names:
                results.append(f"  ✗ {req} — MISSING (run embedder.py)")
                all_ok = False
            else:
                count = client.get_collection(req).count()
                if count == 0:
                    results.append(f"  ✗ {req} — EMPTY (run embedder.py)")
                    all_ok = False
                else:
                    results.append(f"  ✓ {req} — {count} docs")

        for opt in ["tickets_7d", "tickets_30d", "tickets_90d"]:
            if opt in names:
                count = client.get_collection(opt).count()
                results.append(f"  ✓ {opt} — {count} docs")
            else:
                results.append(f"  ⚠ {opt} — not found (optional)")

        return all_ok, "\n".join(results)

    except Exception as e:
        return False, f"  ✗ ChromaDB error: {e}"


def check_memory_file() -> tuple[bool, str]:
    path = CONFIG.memory_file
    if not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            default = {
                "escalations": [], "resolved_patterns": [],
                "customer_notes": {}, "user_preferences": {
                    "default_window": "7d", "preferred_sort": "risk_score",
                    "escalation_threshold": 70
                },
                "session_count": 0, "last_session": None, "feedback_log": []
            }
            with open(path, "w") as f:
                json.dump(default, f, indent=2)
            return True, f"  ✓ Created new memory file at {path}"
        except Exception as e:
            return False, f"  ✗ Cannot create memory file: {e}"

    try:
        with open(path) as f:
            data = json.load(f)
        sessions    = data.get("session_count", 0)
        feedback    = len(data.get("feedback_log", []))
        escalations = len(data.get("escalations", []))
        return True, (
            f"  ✓ Memory file loaded — "
            f"sessions: {sessions}, feedback: {feedback}, "
            f"escalations: {escalations}"
        )
    except json.JSONDecodeError as e:
        return False, f"  ✗ Memory file corrupt: {e}"


def check_log_dir() -> tuple[bool, str]:
    try:
        os.makedirs(CONFIG.logs_dir, exist_ok=True)
        test_file = os.path.join(CONFIG.logs_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return True, f"  ✓ Logs directory writable: {CONFIG.logs_dir}"
    except Exception as e:
        return False, f"  ✗ Logs directory not writable: {e}"


def check_latency_baseline() -> tuple[bool, str]:
    """Make one real LLM call to confirm API reachability + measure latency."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return False, "  ✗ Skipped — API key not set"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        start  = time.time()
        resp   = client.chat.completions.create(
            model=CONFIG.model,
            max_tokens=5,
            messages=[{"role": "user", "content": "Reply: ok"}]
        )
        latency = round((time.time() - start) * 1000)
        reply   = resp.choices[0].message.content.strip()
        return True, (
            f"  ✓ LLM reachable — baseline latency: {latency}ms | "
            f"response: '{reply}'"
        )
    except Exception as e:
        return False, f"  ✗ LLM unreachable: {e}"


# ── Main runner ───────────────────────────────────────────────────

def run_health_check(include_llm_ping: bool = True) -> bool:
    print("\n" + "="*60)
    print("SUPPORTDESK AGENT — DEPLOYMENT HEALTH CHECK")
    print("="*60)

    # Show where .env was loaded from (helps debug key issues)
    if _env_path:
        print(f"\n.env loaded from: {_env_path}")
    else:
        print("\n.env not found — using system environment variables")

    checks = [
        ("Environment (API key)",  check_env),
        ("Data files",             check_data_files),
        ("ChromaDB collections",   check_chromadb),
        ("Memory file",            check_memory_file),
        ("Log directory",          check_log_dir),
    ]
    if include_llm_ping:
        checks.append(("LLM connectivity", check_latency_baseline))

    all_passed = True
    for name, fn in checks:
        print(f"\n[{name}]")
        try:
            ok, message = fn()
            print(message)
            if not ok:
                all_passed = False
                print(f"  → FAILED: {name}")
        except Exception as e:
            print(f"  ✗ Check crashed: {e}")
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("✅ All checks passed — agent ready to serve queries")
    else:
        print("❌ Health check failed — fix errors above before proceeding")
    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    ok = run_health_check()
    sys.exit(0 if ok else 1)
