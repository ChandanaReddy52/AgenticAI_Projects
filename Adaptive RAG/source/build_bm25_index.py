#build_bm25_index.py
# build_bm25_index.py

import json
import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi

# ---------------------------------------------------
# Paths
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_DIR / "data" / "dataset v1" / "unified_chunks.json"

INDEX_DIR = BASE_DIR / "indexes"

BM25_INDEX_PATH = INDEX_DIR / "bm25_index.pkl"
BM25_DOCS_PATH = INDEX_DIR / "bm25_docs.json"

# ---------------------------------------------------
# Load chunks
# ---------------------------------------------------

print("Loading unified chunks...")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} chunks")

# ---------------------------------------------------
# Tokenization
# ---------------------------------------------------

def tokenize(text):
    return text.lower().split()


tokenized_corpus = []
docs = []

for chunk in chunks:

    tokens = tokenize(chunk["text"])
    tokenized_corpus.append(tokens)

    docs.append({
        "chunk_id": chunk["chunk_id"],
        "document_type": chunk["document_type"],
        "chapter": chunk["chapter"],
        "section": chunk["section"],
        "text": chunk["text"]
    })

# ---------------------------------------------------
# Build BM25 index
# ---------------------------------------------------

print("Building BM25 index...")

bm25 = BM25Okapi(tokenized_corpus)

# ---------------------------------------------------
# Save index
# ---------------------------------------------------

print("Saving BM25 index...")

with open(BM25_INDEX_PATH, "wb") as f:
    pickle.dump(bm25, f)

with open(BM25_DOCS_PATH, "w", encoding="utf-8") as f:
    json.dump(docs, f, indent=2)

print("BM25 index saved to:", BM25_INDEX_PATH)
print("BM25 docs saved to:", BM25_DOCS_PATH)