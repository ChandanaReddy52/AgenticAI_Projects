# memory_index.py
# Build FAISS index for agent memory
import os
import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

MEMORY_PATH = os.path.join(ARTIFACTS_DIR, "agent_memory.csv")
MEMORY_INDEX_PATH = os.path.join(ARTIFACTS_DIR, "memory_faiss_index.bin")
MEMORY_META_PATH = os.path.join(ARTIFACTS_DIR, "memory_metadata.csv")


def build_memory_index():
    """
    Build FAISS index for agent memory.
    This must be run explicitly and NEVER at import time.
    """
    # Load memory
    memory_df = pd.read_csv(MEMORY_PATH)

    # Embed memory content
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = memory_df["content"].tolist()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    ).astype("float32")

    # Build FAISS index (cosine via inner product)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Save artifacts
    faiss.write_index(index, MEMORY_INDEX_PATH)
    memory_df.to_csv(MEMORY_META_PATH, index=False)

    print(f"Memory index built with {index.ntotal} entries.")


# Memory indexing must NEVER happen accidentally, so we guard it behind main
if __name__ == "__main__":
    build_memory_index()
