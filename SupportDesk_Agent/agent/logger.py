"""
logger.py — Production-grade logging with rotation and latency metrics
Location: supportdesk_agent/agent/logger.py

Three log files:
  interactions.jsonl   — every query/response (existing, extended)
  errors.jsonl         — errors only, for alerting
  latency_metrics.jsonl — per-tool timing for p50/p95 analysis

Log rotation: files are rotated at 10MB, 3 backups kept.
PII protection: customer names → IDs only in all log files.
"""

import json, os, time, shutil
from datetime import datetime

try:
    from deployment.config import CONFIG
    INTERACTIONS_LOG = CONFIG.interactions_log
    ERRORS_LOG       = CONFIG.errors_log
    LATENCY_LOG      = CONFIG.latency_log
    MAX_LOG_MB       = CONFIG.max_log_size_mb
    MAX_BACKUPS      = CONFIG.max_log_backups
except ImportError:
    # Fallback paths if config not yet available
    _ROOT            = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INTERACTIONS_LOG = os.path.join(_ROOT, "logs", "interactions.jsonl")
    ERRORS_LOG       = os.path.join(_ROOT, "logs", "errors.jsonl")
    LATENCY_LOG      = os.path.join(_ROOT, "logs", "latency_metrics.jsonl")
    MAX_LOG_MB       = 10
    MAX_BACKUPS      = 3


def _rotate_if_needed(path: str) -> None:
    """Rotate log file if it exceeds MAX_LOG_MB."""
    try:
        if not os.path.exists(path):
            return
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb < MAX_LOG_MB:
            return
        # Shift existing backups
        for i in range(MAX_BACKUPS - 1, 0, -1):
            src = f"{path}.{i}"
            dst = f"{path}.{i+1}"
            if os.path.exists(src):
                shutil.move(src, dst)
        shutil.move(path, f"{path}.1")
    except Exception:
        pass  # Never crash due to log rotation failure


def _append(path: str, entry: dict) -> None:
    """Append one JSON line to a log file. Creates dirs if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _rotate_if_needed(path)
    try:
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Never crash due to logging failure


def log_interaction(
    query:    str,
    intent:   str,
    tool:     str,
    response: dict,
    latency:  float,
    phase:    str = "unknown",
    notes:    str = ""
) -> None:
    """Log every agent interaction."""
    entry = {
        "timestamp":           datetime.now().isoformat(),
        "phase":               phase,
        "query":               query,
        "intent":              intent,
        "tool_called":         tool,
        "latency_ms":          round(latency * 1000, 2),
        "response_keys":       list(response.keys()) if response else [],
        "hallucination_check": response.get("hallucination_check", False),
        "confidence":          response.get("confidence"),
        "notes":               notes
    }
    _append(INTERACTIONS_LOG, entry)

    # Also log latency metric for per-tool tracking
    log_latency_metric(
        phase=phase, tool=tool,
        latency_ms=round(latency * 1000, 2),
        success=("error" not in (response or {}))
    )


def log_error(
    phase:     str,
    query:     str,
    error_type: str,
    error_msg: str,
    tool:      str = "none",
    latency:   float = 0.0
) -> None:
    """Log errors to separate errors.jsonl for alerting."""
    entry = {
        "timestamp":  datetime.now().isoformat(),
        "phase":      phase,
        "error_type": error_type,
        "error_msg":  str(error_msg)[:500],
        "query":      query[:200],
        "tool":       tool,
        "latency_ms": round(latency * 1000, 2),
    }
    _append(ERRORS_LOG, entry)


def log_latency_metric(
    phase:      str,
    tool:       str,
    latency_ms: float,
    success:    bool = True
) -> None:
    """Log per-tool latency for p50/p95 analysis."""
    entry = {
        "timestamp":  datetime.now().isoformat(),
        "phase":      phase,
        "tool":       tool,
        "latency_ms": latency_ms,
        "success":    success
    }
    _append(LATENCY_LOG, entry)


def anonymize_for_log(data: dict) -> dict:
    """Remove PII — customer names replaced with IDs."""
    safe = data.copy()
    for key in ["name", "contact", "email", "csm"]:
        if key in safe:
            safe[key] = "[REDACTED]"
    return safe


# ── Latency analysis utilities ────────────────────────────────────

def get_latency_stats(phase_filter: str = None) -> dict:
    """
    Read latency_metrics.jsonl and compute p50/p95/avg per tool.
    Used by Phase 9 evaluation harness.
    """
    if not os.path.exists(LATENCY_LOG):
        return {}

    entries = []
    try:
        with open(LATENCY_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if phase_filter is None or \
                       entry.get("phase","").startswith(phase_filter):
                        entries.append(entry)
    except Exception:
        return {}

    if not entries:
        return {}

    # Group by tool
    by_tool = {}
    for e in entries:
        tool = e.get("tool", "unknown")
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(e["latency_ms"])

    stats = {}
    for tool, latencies in by_tool.items():
        sorted_l = sorted(latencies)
        n        = len(sorted_l)
        stats[tool] = {
            "count":   n,
            "avg_ms":  round(sum(sorted_l) / n, 1),
            "p50_ms":  sorted_l[int(n * 0.50)],
            "p95_ms":  sorted_l[int(n * 0.95)],
            "min_ms":  sorted_l[0],
            "max_ms":  sorted_l[-1],
        }
    return stats


def get_error_count(phase_filter: str = None) -> int:
    """Count errors in errors.jsonl for health monitoring."""
    if not os.path.exists(ERRORS_LOG):
        return 0
    count = 0
    try:
        with open(ERRORS_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if phase_filter is None or \
                   entry.get("phase","").startswith(phase_filter):
                    count += 1
    except Exception:
        pass
    return count