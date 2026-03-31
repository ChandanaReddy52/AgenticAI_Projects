import os
import faiss
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

#Loading artifacts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

INDEX_PATH = os.path.join(ARTIFACTS_DIR, "faiss_index.bin")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "chunks_metadata.csv")

index = faiss.read_index(INDEX_PATH)
df_chunks = pd.read_csv(METADATA_PATH)

#Model setup
model = SentenceTransformer("all-MiniLM-L6-v2")

#Evaluation queries and their relevant documents
EVAL_QUERIES = [
    {
        "query": "What can you build using Notion?",
        "relevant_docs": {"D01"}
    },
    {
        "query": "How to add a new page on phone?",
        "relevant_docs": {"D03"}
    },
    {
        "query": "How can I organize my pages in Notion?",
        "relevant_docs": {"D05"}
    },
    {
        "query": "How can I send my template to my friend?",
        "relevant_docs": {"D07", "D08"}
    },
    {
        "query": "How to tag my colleague on my page?",
        "relevant_docs": {"D09"}
    },
    {
        "query": "How to reset my Notion password?",
        "relevant_docs": {"D10", "D20"}
    },
    {
        "query": "What to do if I want to export my workspace data?",
        "relevant_docs": {"D12"}
    },
    {
        "query": "How can I use advanced security features in Notion?",
        "relevant_docs": {"D15"}
    },
    {
        "query": "How to remove access for my data for support team?",
        "relevant_docs": {"D16"}
    },
    {
        "query": "How to authenticate using passkey in my phone?",
        "relevant_docs": {"D18"}
    },
    {
        "query": "How to reset Notion on tablet?",
        "relevant_docs": {"D19"}
    },
    {
        "query": "Help me restore my data, I lost my content?",
        "relevant_docs": {"D20"}
    },
    {
        "query": "I don’t have permission to use my own page, what to do?",
        "relevant_docs": {"D21"}
    },
    {
        "query": "Help me fix upload error for my image",
        "relevant_docs": {"D22"}
    }
]

#Helper: to extract doc_id from filename
def get_doc_id_from_filename(filename: str) -> str:
    # example: notion_page_03.txt -> D03
    num = filename.split("_")[2].split(".")[0]
    return f"D{num.zfill(2)}"

#Core evaluation function
def evaluate_recall_at_k(
    eval_queries,
    model,
    index,
    df_chunks,
    k=5
):
    results = []

    for item in eval_queries:
        query = item["query"]
        relevant_docs = item["relevant_docs"]

        # Encode query
        query_emb = model.encode(
            [query],
            normalize_embeddings=True
        ).astype("float32")

        # Search
        scores, indices = index.search(query_emb, k)

        retrieved_docs = set()
        for idx in indices[0]:
            filename = df_chunks.iloc[idx]["filename"]
            doc_id = get_doc_id_from_filename(filename)
            retrieved_docs.add(doc_id)

        hit = len(relevant_docs & retrieved_docs) > 0

        results.append({
            "query": query,
            "expected": relevant_docs,
            "retrieved": retrieved_docs,
            "recall_at_5": int(hit)
        })

    return results

#Run evaluation + summary
results = evaluate_recall_at_k(
    EVAL_QUERIES,
    model,
    index,
    df_chunks,
    k=5
)

total = len(results)
hits = sum(r["recall_at_5"] for r in results)

print(f"\nOVERALL Recall@5 = {hits}/{total} = {hits/total:.2f}\n")

for r in results:
    print("Query:", r["query"])
    print("Expected:", r["expected"])
    print("Retrieved:", r["retrieved"])
    print("Recall@5:", r["recall_at_5"])
    print("-" * 60)
