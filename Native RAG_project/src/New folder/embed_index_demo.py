# embed_index.py
import os
import pandas as pd
from chunking import chunk_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "dataset_v1_notion", "raw")

documents = [] # List to hold all document chunks

for fname in os.listdir(DATA_DIR):
    if fname.endswith(".txt"): # Process only text files
        with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
            #Raw document → list of chunks
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


# Embedding generation
# semantics become numeric geometry/embedding space

from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2") # lightweight, efficient model

texts = df_chunks["text"].tolist() # list of chunk texts

#converting text into numbers such that semantic meaning becomes geometric distance.
embeddings = model.encode(
    texts,
    batch_size=16,
    show_progress_bar=True,
    #projects vectors onto the unit sphere so cosine similarity is valid
    normalize_embeddings=True  # Normalize to unit vectors because cosine similarity is often used (dot product of unit vectors)
)

embeddings = np.array(embeddings).astype("float32")
print("Embedding shape:", embeddings.shape)

# FAISS index creation
import faiss

dimension = embeddings.shape[1]

index = faiss.IndexFlatIP(dimension) #Cosine similarity in FAISS = Inner Product on normalized vectors.
index.add(embeddings)

print("FAISS index size:", index.ntotal)

# Save index and metadata
faiss.write_index(index, "faiss_index.bin")
df_chunks.to_csv("chunks_metadata.csv", index=False)



# Example query for sanity check
query = "how to create a block in notion?"
query_emb = model.encode(
    [query],
    normalize_embeddings=True
).astype("float32")

scores, indices = index.search(query_emb, k=5)

for rank, idx in enumerate(indices[0]):
    print(f"\nRank {rank+1} | Score: {scores[0][rank]:.4f}")
    print(df_chunks.iloc[idx]["text"][:300], "...")

