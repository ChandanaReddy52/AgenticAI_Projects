#To manage persistent agent memory 
# Memory CRUD (write / store / load) & Memory retrieval logic (semantic selection)) 
# memory.py
import os
import pandas as pd
from datetime import datetime
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_PATH = os.path.join(BASE_DIR, "artifacts", "agent_memory.csv")

MEMORY_COLUMNS = [
    "memory_id",
    "timestamp",
    "memory_type",
    "content",
    "importance"
]


def load_memory():
    """
    Load agent memory from disk.
    If memory file does not exist, return empty DataFrame.
    """
    if not os.path.exists(MEMORY_PATH):
        return pd.DataFrame(columns=MEMORY_COLUMNS)

    return pd.read_csv(MEMORY_PATH)


def write_memory(memory_type, content, importance="medium"):
    """
    Write a new memory entry to persistent storage.
    """
    memory = load_memory()

    new_entry = {
        "memory_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "memory_type": memory_type,
        "content": content,
        "importance": importance
    }

    memory = pd.concat([memory, pd.DataFrame([new_entry])], ignore_index=True)
    memory.to_csv(MEMORY_PATH, index=False)

'''
def retrieve_memory(memory_type=None):
    """
    Retrieve memory entries.
    Optionally filter by memory type.
    """
    memory = load_memory()

    if memory_type:
        memory = memory[memory["memory_type"] == memory_type]

    return memory
'''

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MEMORY_INDEX_PATH = os.path.join(BASE_DIR, "artifacts", "memory_faiss_index.bin")
MEMORY_META_PATH = os.path.join(BASE_DIR, "artifacts", "memory_metadata.csv")

model = SentenceTransformer("all-MiniLM-L6-v2")

# Always load global preference memories
def load_global_memory():
    memory = pd.read_csv(MEMORY_META_PATH)
    return memory[memory["memory_type"] == "global_preference"]["content"].tolist()

# Semantically retrieve contextual memory
def retrieve_contextual_memory(query, k=3, threshold=0.6):
    """
    Retrieve semantically relevant memory entries.
    Returns empty list if nothing meets precision threshold.
    """
    if not os.path.exists(MEMORY_INDEX_PATH):
        return []

    index = faiss.read_index(MEMORY_INDEX_PATH)
    memory_df = pd.read_csv(MEMORY_META_PATH)

    query_emb = model.encode(
        [query],
        normalize_embeddings=True
    ).astype("float32")

    scores, indices = index.search(query_emb, k)

    relevant_memories = []
    for score, idx in zip(scores[0], indices[0]):
        if score >= threshold:
            relevant_memories.append(memory_df.iloc[idx]["content"])

    return relevant_memories
