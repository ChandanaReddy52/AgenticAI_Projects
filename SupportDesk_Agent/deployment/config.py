"""
config.py — Centralised deployment configuration
Location: supportdesk_agent/deployment/config.py

IMPORTANT: Always import this AFTER loading .env.
           health_check.py and run.sh both load .env first.
           If you import this at module top-level before .env is loaded,
           os.getenv("OPENAI_API_KEY") will return None.
"""

import os
from dataclasses import dataclass, field


def _find_project_root() -> str:
    """Walk up from this file to find supportdesk_agent/ root."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        if os.path.exists(os.path.join(current, "main.py")):
            return current
        current = os.path.dirname(current)
    raise RuntimeError(
        "Cannot locate project root — is main.py present?\n"
        f"Searched from: {os.path.dirname(os.path.abspath(__file__))}"
    )


PROJECT_ROOT = _find_project_root()


@dataclass
class DeploymentConfig:
    # ── Paths ───────────────────────────────────────────────────
    project_root:      str = PROJECT_ROOT
    data_dir:          str = os.path.join(PROJECT_ROOT, "data")
    logs_dir:          str = os.path.join(PROJECT_ROOT, "logs")
    chroma_dir:        str = os.path.join(PROJECT_ROOT, "data", "chroma_db")
    memory_file:       str = os.path.join(PROJECT_ROOT, "data",
                                          "long_term_memory.json")
    tickets_file:      str = os.path.join(PROJECT_ROOT, "data", "tickets.json")
    customers_file:    str = os.path.join(PROJECT_ROOT, "data", "customers.json")

    # ── Log files ───────────────────────────────────────────────
    interactions_log:  str = os.path.join(PROJECT_ROOT, "logs",
                                          "interactions.jsonl")
    errors_log:        str = os.path.join(PROJECT_ROOT, "logs",
                                          "errors.jsonl")
    latency_log:       str = os.path.join(PROJECT_ROOT, "logs",
                                          "latency_metrics.jsonl")

    # ── LLM settings ────────────────────────────────────────────
    model:             str = "gpt-4o-mini"
    temperature:       float = 0.1
    max_tokens:        int = 1500
    llm_timeout_sec:   int = 30
    llm_max_retries:   int = 2

    # ── Agent limits ─────────────────────────────────────────────
    max_iterations:    int = 5
    memory_window:     int = 6
    retrieval_top_k:   int = 12

    # ── Log rotation ─────────────────────────────────────────────
    max_log_size_mb:   int = 10
    max_log_backups:   int = 3

    # ── Fallback chain ───────────────────────────────────────────
    fallback_chain: list = field(default_factory=lambda: [
        "adaptive",
        "langchain",
        "llm",
        "baseline"
    ])

    # ── Feature flags ────────────────────────────────────────────
    enable_rag:           bool = True
    enable_memory:        bool = True
    enable_adaptation:    bool = True
    enable_log_rotation:  bool = True
    verbose_mode:         bool = False

    def validate(self) -> list[str]:
        """Check all required resources exist. Returns error list."""
        errors = []
        for name, path in [
            ("tickets.json",   self.tickets_file),
            ("customers.json", self.customers_file),
        ]:
            if not os.path.exists(path):
                errors.append(f"Missing: {name} at {path}")

        for name, path in [
            ("data/",       self.data_dir),
            ("chroma_db/",  self.chroma_dir),
        ]:
            if not os.path.isdir(path):
                errors.append(f"Missing directory: {name} at {path}")

        # API key — read at call time, not import time
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            errors.append("OPENAI_API_KEY not set")
        elif not api_key.startswith("sk-"):
            errors.append("OPENAI_API_KEY format invalid")

        os.makedirs(self.logs_dir, exist_ok=True)
        return errors


# Singleton
CONFIG = DeploymentConfig()
