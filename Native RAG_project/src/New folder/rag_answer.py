import os
import faiss
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # Load .env into os.environ

#Loading artifacts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

INDEX_PATH = os.path.join(ARTIFACTS_DIR, "faiss_index.bin")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "chunks_metadata.csv")

index = faiss.read_index(INDEX_PATH)
df_chunks = pd.read_csv(METADATA_PATH)

model = SentenceTransformer("all-MiniLM-L6-v2")

#Retrieval function (Top-K chunks)
def retrieve_chunks(query, k=5):
    query_emb = model.encode(
        [query],
        normalize_embeddings=True
    ).astype("float32")
    
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


#Prompt construction function
def build_prompt(query, chunks):
    context = "\n\n".join(
        f"Chunk {c['rank']}:\n{c['text']}" for c in chunks
    )

    #role + task definition with instructions + context + question
    prompt = f"""
        You are a technical documentation assistant.

        Answer the question using ONLY the information provided in the context below.
        Do NOT use prior knowledge.
        If the answer is not present in the context, say:
        "I don't have enough information to answer this."

        Context:
        {context}

        Question:
        {query}

        Answer:
        """.strip()

    return prompt

#OpenAI API call function
client = OpenAI()  # API key is automatically read from environment variables

def generate_answer(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.0 #deterministic output -> grounded in context
    )

    return response.choices[0].message.content

# Example usage
if __name__ == "__main__":

    query = "How do I reset my Notion password?"
    #stress test questions
    #query = "How much does Notion cost per month?"
    #query = "Does Notion store data in India?"

    chunks = retrieve_chunks(query, k=5)

    print("\n--- Retrieved Chunks ---\n")
    for c in chunks:
        print(f"Rank {c['rank']} | Score {c['score']:.4f}")
        print(c["text"][:300], "\n")

    prompt = build_prompt(query, chunks)
    answer = generate_answer(prompt)

    print("\n--- RAG Answer ---\n")
    print(answer)
