# debug_retrieval.py
import json
import faiss
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

# ---------------------------------------------------
# Paths
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "indexes"

FAISS_INDEX_PATH = INDEX_DIR / "vector_index.faiss"
VECTOR_METADATA_PATH = INDEX_DIR / "vector_metadata.json"

BM25_INDEX_PATH = INDEX_DIR / "bm25_index.pkl"
BM25_DOCS_PATH = INDEX_DIR / "bm25_docs.json"

# ---------------------------------------------------
# Load model
# ---------------------------------------------------

print("Loading embedding model...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# ---------------------------------------------------
# Load FAISS
# ---------------------------------------------------

print("Loading FAISS index...")
faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))

with open(VECTOR_METADATA_PATH, "r", encoding="utf-8") as f:
    vector_metadata = json.load(f)

# ---------------------------------------------------
# Load BM25
# ---------------------------------------------------

print("Loading BM25 index...")

with open(BM25_INDEX_PATH, "rb") as f:
    bm25 = pickle.load(f)

with open(BM25_DOCS_PATH, "r", encoding="utf-8") as f:
    bm25_docs = json.load(f)

# ---------------------------------------------------
# Query
# ---------------------------------------------------

query = input("\nEnter query: ")

# ---------------------------------------------------
# FAISS Search
# ---------------------------------------------------

print("\n--- FAISS RESULTS ---")

query_embedding = model.encode(
    [query],
    normalize_embeddings=True
)

scores, indices = faiss_index.search(
    np.array(query_embedding),
    5
)

for score, idx in zip(scores[0], indices[0]):

    chunk = vector_metadata[idx]

    print("\nScore:", score)
    print("Doc:", chunk["document_type"])
    print("Chapter:", chunk["chapter"])
    print("Text:", chunk["text"][:200], "...")

# ---------------------------------------------------
# BM25 Search
# ---------------------------------------------------

print("\n--- BM25 RESULTS ---")

query_tokens = query.lower().split()

bm25_scores = bm25.get_scores(query_tokens)

top_indices = np.argsort(bm25_scores)[::-1][:5]

for idx in top_indices:

    doc = bm25_docs[idx]

    print("\nScore:", bm25_scores[idx])
    print("Doc:", doc["document_type"])
    print("Chapter:", doc["chapter"])
    print("Text:", doc["text"][:200], "...")