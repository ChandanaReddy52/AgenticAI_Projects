# retrieval.py - functions for retrieving knowledge chunks from vector store
# FAISS + embedding + retrieve_chunks
import os
import faiss
import pandas as pd
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv


load_dotenv()  # Load .env into os.environ

#Loading artifacts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

INDEX_PATH = os.path.join(ARTIFACTS_DIR, "faiss_index.bin")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "chunks_metadata.csv")

# Check if artifacts exist
if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
    raise FileNotFoundError(
        "FAISS index or metadata not found. Run embed_index.py first."
    )

index = faiss.read_index(INDEX_PATH)
df_chunks = pd.read_csv(METADATA_PATH)

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

#Retrieval function (Top-K chunks)
def retrieve_chunks(query: str, k: int = 5) -> List[Dict[str, Any]]:
    query_emb = model.encode(
        [query],
        normalize_embeddings=True
    ).astype("float32") # retrieve normalized embeddings
    
    #index search for top-k similar chunks with cosine similarity for normalized vectors
    scores, indices = index.search(query_emb, k)

    chunks = []
    # Collecting chunk info
    for rank, idx in enumerate(indices[0]):
        chunks.append({
            "rank": rank + 1, #ranking the chunks
            "text": df_chunks.iloc[idx]["text"], #locating chunk text
            "filename": df_chunks.iloc[idx]["filename"], #locating source filename
            "score": scores[0][rank] #similarity score
        }) 

    return chunks


