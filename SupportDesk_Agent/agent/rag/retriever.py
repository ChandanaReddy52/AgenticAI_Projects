"""
retriever.py — Query-time semantic search over ChromaDB
Location: supportdesk_agent/agent/rag/retriever.py

Uses the same custom OpenAIEmbedder (openai >= 1.0.0) as embedder.py.
"""

import os, sys

# ── Path resolution ───────────────────────────────────────────────
__file__abs  = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__abs)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CHROMA_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")

# ── Find .env anywhere up the directory tree ──────────────────────
def _find_env(start: str):
    current = start
    for _ in range(6):
        candidate = os.path.join(current, ".env")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None

OPENAI_KEY = None
try:
    from dotenv import load_dotenv
    env = _find_env(PROJECT_ROOT)
    if env:
        load_dotenv(env)
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
except ImportError:
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ── ChromaDB + custom embedder ────────────────────────────────────
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


class OpenAIEmbedder(EmbeddingFunction):
    """Same custom embedder as embedder.py — uses openai >= 1.0.0 API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        super().__init__()
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model  = model

    @staticmethod
    def name() -> str:
        return "openai-text-embedding-3-small"

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
        response = self._client.embeddings.create(input=input, model=self._model)
        return [item.embedding for item in response.data]


# ── Lazy singletons ───────────────────────────────────────────────
_client = None
_ef     = None


def _get_client():
    global _client
    if _client is None:
        if not os.path.isdir(CHROMA_PATH):
            raise RuntimeError(
                f"ChromaDB not found at: {CHROMA_PATH}\n"
                "Run: python agent/rag/embedder.py"
            )
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def _get_ef():
    global _ef
    if _ef is None:
        if not OPENAI_KEY:
            raise ValueError(
                "OPENAI_API_KEY not set. "
                "Check your .env file or environment variables."
            )
        _ef = OpenAIEmbedder(api_key=OPENAI_KEY)
    return _ef


def _get_collection(name: str):
    client = _get_client()
    try:
        return client.get_collection(name=name, embedding_function=_get_ef())
    except Exception as e:
        raise RuntimeError(
            f"Collection '{name}' not found.\n"
            f"Run: python agent/rag/embedder.py\n"
            f"Detail: {e}"
        )


# ── Public retrieval functions ────────────────────────────────────

def retrieve_tickets(
    query:       str,
    window:      str  = "all",
    top_k:       int  = 8,
    priority:    str  = None,
    customer_id: str  = None,
    status_in:   list = None,
) -> list:
    """
    Semantic search over tickets.
    Returns list of dicts: {id, document, metadata, distance, relevance}
    """
    col_name   = f"tickets_{window}" if window != "all" else "tickets_all"
    collection = _get_collection(col_name)

    # Build metadata filter
    conditions = []
    if priority:
        conditions.append({"priority": {"$eq": priority}})
    if customer_id:
        conditions.append({"customer_id": {"$eq": customer_id}})
    if status_in:
        conditions.append({"status": {"$in": status_in}})

    where = {}
    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    n = min(top_k, collection.count())
    if n == 0:
        return []

    kwargs = {
        "query_texts": [query],
        "n_results":   n,
        "include":     ["documents", "metadatas", "distances"]
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    docs = []
    for i in range(len(results["ids"][0])):
        docs.append({
            "id":        results["ids"][0][i],
            "document":  results["documents"][0][i],
            "metadata":  results["metadatas"][0][i],
            "distance":  results["distances"][0][i],
            "relevance": round(1 - results["distances"][0][i], 4)
        })

    # Priority boost
    boost_map = {"critical": 0.15, "high": 0.08, "medium": 0.02, "low": 0.0}
    for doc in docs:
        doc["relevance"] += boost_map.get(doc["metadata"].get("priority","low"), 0.0)

    docs.sort(key=lambda x: -x["relevance"])
    return docs


def retrieve_all_customers(query: str = "customer churn risk ARR health") -> list:
    """
    Retrieve ALL customers — guaranteed complete set.
    Fixes Q3 Phase 3 failure (LLM received truncated customer list).
    Returns all customers sorted by risk_score descending.
    """
    collection = _get_collection("customers_all")
    count      = collection.count()
    if count == 0:
        return []

    # n_results = count guarantees every customer is retrieved
    results = collection.query(
        query_texts=[query],
        n_results=count,
        include=["documents", "metadatas", "distances"]
    )

    docs = []
    for i in range(len(results["ids"][0])):
        docs.append({
            "id":       results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
        })

    # Sort by pre-computed risk_score (highest risk first)
    docs.sort(key=lambda x: -x["metadata"].get("risk_score", 0))
    return docs


def retrieve_sla_at_risk(lookahead_hours: int = 24) -> list:
    """
    Retrieve tickets at SLA risk.
    Rule engine computes hours_until_breach (deterministic),
    then fetches full document context for each at-risk ticket.
    """
    from agent.tools import predict_sla_risk

    rule_result  = predict_sla_risk(lookahead_hours=lookahead_hours)
    at_risk_ids  = [r["ticket_id"] for r in rule_result.get("at_risk", [])]
    breached_ids = rule_result.get("already_breached", [])
    all_ids      = at_risk_ids + breached_ids

    if not all_ids:
        return []

    collection = _get_collection("tickets_all")
    try:
        results = collection.get(
            ids=all_ids,
            include=["documents", "metadatas"]
        )
    except Exception as e:
        print(f"[RETRIEVER] SLA fetch error: {e}")
        return []

    docs = []
    for i in range(len(results["ids"])):
        tid  = results["ids"][i]
        meta = dict(results["metadatas"][i])
        sla  = next((r for r in rule_result.get("at_risk", [])
                     if r["ticket_id"] == tid), {})
        meta["hours_until_breach"] = sla.get("hours_until_breach", -1)
        meta["breach_probability"] = sla.get("breach_probability", 1.0)
        meta["is_breached"]        = tid in breached_ids
        docs.append({
            "id":       tid,
            "document": results["documents"][i],
            "metadata": meta
        })

    docs.sort(key=lambda x: (
        0 if x["metadata"].get("is_breached") else 1,
        x["metadata"].get("hours_until_breach", 999)
    ))
    return docs


def retrieve_patterns(window: str = "7d", top_k: int = 10) -> list:
    """Retrieve tickets for pattern detection — uses pattern-optimised query."""
    query = (
        "sync failure offline duplicate orders retry idempotency "
        "data loss SLA breach billing compliance audit"
    )
    return retrieve_tickets(query=query, window=window, top_k=top_k)
