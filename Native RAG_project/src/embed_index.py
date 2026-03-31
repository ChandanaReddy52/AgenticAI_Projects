# embed_index.py
import os
import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from chunking import chunk_text

# ------------------------
# Path setup
# ------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "dataset_v1_notion", "raw")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ------------------------
# Load + chunk documents
# ------------------------

documents = []  # List to hold all document chunks

# Iterate over files in the data directory
for fname in os.listdir(DATA_DIR):
    if fname.endswith(".txt"):  # Process only text files
        with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
            # Raw document → list of chunks
            text = f.read()
            chunks = chunk_text(text)

            # Append each chunk with metadata
            for i, chunk in enumerate(chunks):
                documents.append({
                    "filename": fname,
                    "chunk_id": i,
                    "text": chunk
                })

df_chunks = pd.DataFrame(documents)
print("Total chunks:", len(df_chunks))

# ------------------------
# Embedding generation
# ------------------------
# semantics become numeric geometry / embedding space

model = SentenceTransformer("all-MiniLM-L6-v2")  
# lightweight, efficient SBERT-style model

texts = df_chunks["text"].tolist()  
# list of chunk texts

# converting text into numbers such that semantic meaning becomes geometric distance
embeddings = model.encode(
    texts,
    batch_size=16,
    show_progress_bar=True,
    # projects vectors onto the unit sphere so cosine similarity is valid
    normalize_embeddings=True
)

embeddings = np.array(embeddings).astype("float32")
print("Embedding shape:", embeddings.shape)

# ------------------------
# FAISS index creation
# ------------------------

dimension = embeddings.shape[1]

# Cosine similarity in FAISS = Inner Product on normalized vectors
index = faiss.IndexFlatIP(dimension)
index.add(embeddings)

print("FAISS index size:", index.ntotal)

# ------------------------
# Save index and metadata (FREEZE)
# ------------------------

faiss.write_index(
    index,
    os.path.join(ARTIFACTS_DIR, "faiss_index.bin")
)

df_chunks.to_csv(
    os.path.join(ARTIFACTS_DIR, "chunks_metadata.csv"),
    index=False
)

print("Index and metadata saved to artifacts/")
