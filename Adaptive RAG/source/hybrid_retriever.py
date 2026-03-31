import json
import faiss
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer, CrossEncoder

from query_rewriter import rewrite_query


# ---------------------------------------------------
# Paths
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "indexes"

FAISS_INDEX_PATH = INDEX_DIR / "vector_index.faiss"
VECTOR_METADATA_PATH = INDEX_DIR / "vector_metadata.json"
BM25_INDEX_PATH = INDEX_DIR / "bm25_index.pkl"


# ---------------------------------------------------
# Retrieval configuration
# ---------------------------------------------------

VECTOR_K = 20
BM25_K = 20
RRF_K = 60


# ---------------------------------------------------
# Query dependent context size
# ---------------------------------------------------

def decide_top_k(query):

    q = query.lower()

    if any(k in q for k in ["how", "procedure", "steps", "repair"]):
        return 8

    if any(k in q for k in ["what is", "what does", "meaning"]):
        return 3

    return 5


# ---------------------------------------------------
# Metadata boosting
# ---------------------------------------------------

def metadata_boost(chunk, query):

    score = 0
    q = query.lower()

    doc_type = chunk.get("document_type")

    if "recall" in q and doc_type == "recall":
        score += 0.2

    if "warranty" in q and doc_type == "warranty":
        score += 0.2

    if any(k in q for k in ["brake", "abs", "esc"]):

        components = chunk.get("component_categories", [])

        if components:
            score += 0.1

    return score


# ---------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------

def rrf_fusion(vector_results, bm25_results):

    scores = {}

    for rank, r in enumerate(vector_results):
        cid = r["chunk_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (RRF_K + rank + 1)

    for rank, r in enumerate(bm25_results):
        cid = r["chunk_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (RRF_K + rank + 1)

    return scores


# ---------------------------------------------------
# Duplicate filtering
# ---------------------------------------------------

def remove_duplicates(chunks):

    seen = set()
    unique = []

    for c in chunks:

        cid = c["chunk_id"]

        if cid not in seen:
            unique.append(c)
            seen.add(cid)

    return unique

# ---------------------------------------------------
# Vector similarity filter (Perplexity trick)
# ---------------------------------------------------

def vector_similarity_filter(results, threshold=0.25):

    filtered = []

    for r in results:
        if r["score"] >= threshold:
            filtered.append(r)

    return filtered

# ---------------------------------------------------
# Hybrid Retriever
# ---------------------------------------------------

class HybridRetriever:

    def __init__(self):

        print("Loading embedding model...")
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        print("Loading reranker model...")
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        print("Loading FAISS index...")
        self.index = faiss.read_index(str(FAISS_INDEX_PATH))

        print("Loading metadata...")
        with open(VECTOR_METADATA_PATH, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        print("Loading BM25 index...")
        with open(BM25_INDEX_PATH, "rb") as f:
            self.bm25 = pickle.load(f)


    # ---------------------------------------------------
    # Vector search
    # ---------------------------------------------------

    def vector_search(self, query):

        emb = self.model.encode([query], normalize_embeddings=True)

        scores, ids = self.index.search(np.array(emb).astype("float32"), VECTOR_K)

        results = []

        for score, idx in zip(scores[0], ids[0]):

            if idx == -1:
                continue

            chunk = self.metadata[idx]

            results.append({
                "chunk_id": chunk["chunk_id"],
                "score": float(score),
                "chunk": chunk
            })

        return results


    # ---------------------------------------------------
    # BM25 search
    # ---------------------------------------------------

    def bm25_search(self, query):

        tokens = query.lower().split()

        scores = self.bm25.get_scores(tokens)

        ranked = np.argsort(scores)[::-1][:BM25_K]

        results = []

        for idx in ranked:

            chunk = self.metadata[idx]

            results.append({
                "chunk_id": chunk["chunk_id"],
                "score": float(scores[idx]),
                "chunk": chunk
            })

        return results


    # ---------------------------------------------------
    # Cross encoder reranker
    # ---------------------------------------------------

    def rerank_chunks(self, query, chunks, top_k):

        if not chunks:
            return []

        pairs = [(query, chunk["text"]) for chunk in chunks]

        scores = self.reranker.predict(pairs)

        ranked = []

        for score, chunk in zip(scores, chunks):
            ranked.append((score, chunk))

        ranked.sort(reverse=True, key=lambda x: x[0])

        return [chunk for score, chunk in ranked[:top_k]]


    # ---------------------------------------------------
    # Main retrieval
    # ---------------------------------------------------

    def retrieve(self, query):

        rewritten_queries = rewrite_query(query)

        vector_results = []
        bm25_results = []

        for q in rewritten_queries:

            vs = self.vector_search(q)

            # remove weak semantic matches
            vs = vector_similarity_filter(vs)

            vector_results.extend(vs)

            bm25_results.extend(self.bm25_search(q))

        # remove duplicates
        vector_results = {r["chunk_id"]: r for r in vector_results}.values()
        bm25_results = {r["chunk_id"]: r for r in bm25_results}.values()

        vector_results = list(vector_results)
        bm25_results = list(bm25_results)

        # RRF fusion
        rrf_scores = rrf_fusion(vector_results, bm25_results)

        merged = {}

        for r in vector_results + bm25_results:

            cid = r["chunk_id"]

            if cid not in merged:
                merged[cid] = r["chunk"]

        scored = []

        for cid, chunk in merged.items():

            score = rrf_scores.get(cid, 0)
            score += metadata_boost(chunk, query)

            scored.append((score, chunk))

        scored.sort(reverse=True, key=lambda x: x[0])

        # Candidate pool
        candidate_chunks = [c for _, c in scored[:40]]

        top_k = decide_top_k(query)

        # Rerank
        final_chunks = self.rerank_chunks(query, candidate_chunks, top_k)

        final_chunks = remove_duplicates(final_chunks)

        return {
            "query": query,
            "context": final_chunks
        }


# ---------------------------------------------------
# Debug
# ---------------------------------------------------

if __name__ == "__main__":

    retriever = HybridRetriever()

    while True:

        query = input("\nEnter query: ")

        if query.lower() in ["exit", "quit"]:
            break

        result = retriever.retrieve(query)

        context = result["context"]

        print("\nRetrieved chunks:\n")

        if not context:
            print("No chunks retrieved.")
            continue

        for c in context:

            print("DOC:", c["document_type"])
            print("CHAPTER:", c.get("chapter"))
            print("TEXT:", c["text"][:300])
            print("-" * 60)