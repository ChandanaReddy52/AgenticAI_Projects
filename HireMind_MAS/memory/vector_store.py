"""
Vector memory layer — Supabase pgvector.

Candidate embeddings live in the candidates.embedding column (vector(1536)).
Similarity search is performed via the match_candidates Supabase RPC function.

Embedding model: text-embedding-3-small (OpenAI), 1536 dimensions.
"""

import logging
from openai import OpenAI
from db.supabase_client import get_client
from config.settings import settings

logger = logging.getLogger(__name__)

_openai: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=settings.openai_api_key)
    return _openai


def embed(text: str) -> list[float]:
    """Embed text using text-embedding-3-small (1536 dims)."""
    response = _get_openai().embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def search_candidates(query_text: str) -> list[dict]:
    """
    Embed query_text and call the match_candidates Supabase RPC function.
    Returns top 5 candidates ordered by cosine similarity.
    Returns an empty list if no candidates are found or the table is empty.

    Each result contains: id, name, email, resume, similarity.
    """
    query_embedding = embed(query_text)

    try:
        result = get_client().rpc(
            "match_candidates",
            {"query_embedding": query_embedding},
        ).execute()
    except Exception:
        logger.exception("match_candidates RPC call failed")
        return []

    return result.data or []
