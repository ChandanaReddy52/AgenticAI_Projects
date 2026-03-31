#build_vector_index.py
import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------
# Paths
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_DIR / "data" / "dataset v1" / "unified_chunks.json"

INDEX_DIR = BASE_DIR / "indexes"
INDEX_DIR.mkdir(exist_ok=True)

FAISS_INDEX_PATH = INDEX_DIR / "vector_index.faiss"
METADATA_PATH = INDEX_DIR / "vector_metadata.json"

# ---------------------------------------------------
# Embedding Model
# ---------------------------------------------------

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)

# ---------------------------------------------------
# Load Chunks
# ---------------------------------------------------

print("Loading unified chunks...")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

texts = []
metadata = []

for chunk in chunks:
    texts.append(chunk["text"])

    metadata.append({
        "chunk_id": chunk["chunk_id"],
        "document_type": chunk["document_type"],
        "document_id": chunk["document_id"],
        "chapter": chunk["chapter"],
        "section": chunk["section"],
        "model": chunk["model"],
        "model_year_start": chunk["model_year_start"],
        "model_year_end": chunk["model_year_end"],
        "publication_year": chunk["publication_year"],
        "text": chunk["text"]
    })

print(f"Loaded {len(texts)} chunks")

# ---------------------------------------------------
# Generate Embeddings
# ---------------------------------------------------

print("Generating embeddings...")

embeddings = model.encode(
    texts,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True # L2 normalization for cosine similarity
)

dimension = embeddings.shape[1]

print(f"Embedding dimension: {dimension}")

# ---------------------------------------------------
# Build FAISS Index
# ---------------------------------------------------

print("Building FAISS index...")

index = faiss.IndexFlatIP(dimension)  # cosine similarity

index.add(embeddings)

print(f"Total vectors indexed: {index.ntotal}")

# ---------------------------------------------------
# Save Index
# ---------------------------------------------------

print("Saving FAISS index...")

faiss.write_index(index, str(FAISS_INDEX_PATH))

print("Saving metadata mapping...")

with open(METADATA_PATH, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print("Index build complete.")

print("FAISS index saved to:", FAISS_INDEX_PATH)
print("Metadata saved to:", METADATA_PATH)