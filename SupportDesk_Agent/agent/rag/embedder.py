"""
embedder.py — Build and persist ChromaDB vector store
Location: supportdesk_agent/agent/rag/embedder.py

FIX: Custom OpenAIEmbedder uses client.embeddings.create()
     (openai >= 1.0.0) instead of chromadb's built-in
     OpenAIEmbeddingFunction which calls the removed openai.Embedding API.

Run: python agent/rag/embedder.py
"""

import os, json, sys
from datetime import datetime

# ── Path resolution ───────────────────────────────────────────────
# agent/rag/embedder.py → dirname×3 = supportdesk_agent/
__file__abs  = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__abs)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CHROMA_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
DATA_PATH   = os.path.join(PROJECT_ROOT, "data")

# ── Find .env anywhere up the directory tree ──────────────────────
def find_env_file(start: str):
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
ENV_PATH   = None

try:
    from dotenv import load_dotenv
    ENV_PATH = find_env_file(PROJECT_ROOT)
    if ENV_PATH:
        load_dotenv(ENV_PATH)
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
except ImportError:
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ── Validate data directory ───────────────────────────────────────
if not os.path.isdir(DATA_PATH):
    print(f"ERROR: data/ not found at: {DATA_PATH}")
    sys.exit(1)

# ── ChromaDB imports ──────────────────────────────────────────────
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


class OpenAIEmbedder(EmbeddingFunction):
    """
    Custom embedder using openai >= 1.0.0 client.embeddings.create() API.
    Fixes: APIRemovedInV1 error from chromadb's built-in embedder.
    """

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
        response = self._client.embeddings.create(
            input=input,
            model=self._model
        )
        return [item.embedding for item in response.data]


def get_embedding_fn() -> OpenAIEmbedder:
    if not OPENAI_KEY:
        hint = (
            f"Found .env at {ENV_PATH} but OPENAI_API_KEY missing inside it."
            if ENV_PATH else
            f"No .env found searching up from {PROJECT_ROOT}"
        )
        raise ValueError(f"OPENAI_API_KEY not set.\n{hint}\n"
                         f".env must contain: OPENAI_API_KEY=sk-...")
    return OpenAIEmbedder(api_key=OPENAI_KEY)


# ── Data loading ──────────────────────────────────────────────────

def load_data():
    for fname in ["tickets.json", "customers.json"]:
        path = os.path.join(DATA_PATH, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{fname} not found at: {path}\n"
                "Run: python data/seed_data.py"
            )
    with open(os.path.join(DATA_PATH, "tickets.json"))   as f: tickets   = json.load(f)
    with open(os.path.join(DATA_PATH, "customers.json")) as f: customers = json.load(f)
    return tickets, customers


def get_window(ticket: dict) -> str:
    try:
        age = (datetime.now() - datetime.fromisoformat(ticket["created_at"])).days
        if age <= 7:  return "7d"
        if age <= 30: return "30d"
        return "90d"
    except Exception:
        return "90d"


# ── Document builders ─────────────────────────────────────────────

def build_ticket_document(ticket: dict, customer: dict) -> tuple:
    tags_str    = ", ".join(ticket.get("tags", []))
    cust_name   = customer.get("name",   "Unknown") if customer else "Unknown"
    cust_arr    = customer.get("arr",    0)          if customer else 0
    cust_health = customer.get("health", 0)          if customer else 0

    doc_text = (
        f"TICKET {ticket['id']}: {ticket['title']}\n"
        f"Description: {ticket['description']}\n"
        f"Priority: {ticket['priority']} | Status: {ticket['status']} "
        f"| Category: {ticket['category']}\n"
        f"Tags: {tags_str}\n"
        f"Customer: {cust_name} | ARR: ${cust_arr:,} | Health: {cust_health}/100\n"
        f"Created: {ticket.get('created_at','')[:10]}"
    )
    metadata = {
        "ticket_id":     ticket["id"],
        "priority":      ticket["priority"],
        "status":        ticket["status"],
        "category":      ticket["category"],
        "customer_id":   ticket["customer_id"],
        "customer_name": cust_name,
        "arr":           float(cust_arr),
        "health":        float(cust_health),
        "tags":          tags_str,
        "window":        get_window(ticket),
        "sentiment":     float(ticket.get("sentiment_score", 5)),
        "created_at":    ticket.get("created_at", "")[:10],
    }
    return doc_text, metadata


def build_customer_document(customer: dict, tickets: list) -> tuple:
    cust_tickets = [t for t in tickets if t["customer_id"] == customer["id"]]
    open_tickets = [t for t in cust_tickets if t["status"] not in ["resolved","closed"]]
    critical     = [t for t in open_tickets if t["priority"] == "critical"]
    churn_tags   = ["churn-risk","vp-escalation","legal","escalation"]
    churn_count  = sum(1 for t in open_tickets
                       if any(tag in t.get("tags",[]) for tag in churn_tags))

    health_risk  = (100 - customer["health"]) * 0.40
    ticket_risk  = min(len(critical) * 15 + len(open_tickets) * 5, 25)
    arr_weight   = min((customer["arr"] / 1500000) * 20, 20)
    churn_weight = min(churn_count * 7.5, 15)
    risk_score   = round(health_risk + ticket_risk + arr_weight + churn_weight, 1)
    risk_label   = ("critical" if risk_score >= 70 else
                    "high"     if risk_score >= 50 else
                    "medium"   if risk_score >= 30 else "low")

    open_titles = "; ".join([t["title"][:60] for t in open_tickets[:5]])
    doc_text = (
        f"CUSTOMER {customer['id']}: {customer['name']}\n"
        f"Industry: {customer['industry']} | Plan: {customer['plan']}\n"
        f"ARR: ${customer['arr']:,} | Health Score: {customer['health']}/100\n"
        f"Risk Score: {risk_score}/100 | Risk Label: {risk_label.upper()}\n"
        f"Open Tickets: {len(open_tickets)} | Critical: {len(critical)} "
        f"| Churn Signals: {churn_count}\n"
        f"CSM: {customer['csm']} | Contact: {customer['contact']}\n"
        f"Active issues: {open_titles or 'None'}"
    )
    metadata = {
        "customer_id":      customer["id"],
        "name":             customer["name"],
        "arr":              float(customer["arr"]),
        "health":           float(customer["health"]),
        "industry":         customer["industry"],
        "plan":             customer["plan"],
        "open_tickets":     len(open_tickets),
        "critical_tickets": len(critical),
        "churn_signals":    churn_count,
        "risk_score":       risk_score,
        "risk_label":       risk_label,
    }
    return doc_text, metadata


# ── Main builder ──────────────────────────────────────────────────

def _drop_if_exists(client, name: str):
    try:
        client.delete_collection(name)
    except Exception:
        pass


def build_collections():
    print(f"\nProject root:  {PROJECT_ROOT}")
    print(f"Data path:     {DATA_PATH}")
    print(f"ChromaDB path: {CHROMA_PATH}")
    print(f"API key from:  {ENV_PATH or 'system environment'}")

    tickets, customers = load_data()
    print(f"\nLoaded: {len(tickets)} tickets, {len(customers)} customers\n")

    ef       = get_embedding_fn()
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client   = chromadb.PersistentClient(path=CHROMA_PATH)
    cust_map = {c["id"]: c for c in customers}

    # tickets_all
    print("Building tickets_all...")
    _drop_if_exists(client, "tickets_all")
    col = client.create_collection("tickets_all", embedding_function=ef)
    docs, metas, ids = [], [], []
    for t in tickets:
        d, m = build_ticket_document(t, cust_map.get(t["customer_id"], {}))
        docs.append(d); metas.append(m); ids.append(t["id"])
    col.add(documents=docs, metadatas=metas, ids=ids)
    print(f"  ✓ tickets_all: {col.count()} documents")

    # customers_all
    print("Building customers_all...")
    _drop_if_exists(client, "customers_all")
    col = client.create_collection("customers_all", embedding_function=ef)
    docs, metas, ids = [], [], []
    for c in customers:
        d, m = build_customer_document(c, tickets)
        docs.append(d); metas.append(m); ids.append(c["id"])
    col.add(documents=docs, metadatas=metas, ids=ids)
    print(f"  ✓ customers_all: {col.count()} documents")

    # windowed collections
    for win in ["7d","30d","90d"]:
        col_name    = f"tickets_{win}"
        win_tickets = [t for t in tickets if get_window(t) == win]
        print(f"Building {col_name}... ({len(win_tickets)} tickets)")
        _drop_if_exists(client, col_name)
        if not win_tickets:
            print(f"  ⚠  {col_name}: no tickets in this window")
            continue
        col = client.create_collection(col_name, embedding_function=ef)
        docs, metas, ids = [], [], []
        for t in win_tickets:
            d, m = build_ticket_document(t, cust_map.get(t["customer_id"], {}))
            docs.append(d); metas.append(m); ids.append(t["id"])
        col.add(documents=docs, metadatas=metas, ids=ids)
        print(f"  ✓ {col_name}: {col.count()} documents")

    # Summary
    print("\n" + "="*50)
    print("✅ All collections built successfully")
    print("="*50)
    print("\nCollection summary:")
    for name in ["tickets_all","customers_all","tickets_7d","tickets_30d","tickets_90d"]:
        try:
            count = client.get_collection(name).count()
            print(f"  ✓  {name:<22} {count} docs")
        except Exception:
            print(f"  ✗  {name:<22} NOT FOUND")

    print(f"\nPersisted to: {CHROMA_PATH}")
    print("\nNext: python main.py --phase 4 --query \"Which customer is most at risk?\"")
    return client


if __name__ == "__main__":
    print("Building ChromaDB vector store...")
    build_collections()
