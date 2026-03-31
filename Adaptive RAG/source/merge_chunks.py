#merge_chunks.py
import json
from pathlib import Path


# ---------------------------------------------------
# Paths
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "dataset v1"

MANUAL_PATH = DATA_DIR / "manual_chunks.json"
RECALL_PATH = DATA_DIR / "recall_chunks.json"
WARRANTY_PATH = DATA_DIR / "warranty_chunks.json"

OUTPUT_PATH = DATA_DIR / "unified_chunks.json"


# ---------------------------------------------------
# Utilities
# ---------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_chunk(chunk):
    """
    Minimal schema validation to protect the pipeline
    """

    required_fields = [
        "chunk_id",
        "document_id",
        "document_type",
        "model",
        "model_year_start",
        "model_year_end",
        "publication_year",
        "text"
    ]

    for field in required_fields:
        if field not in chunk:
            raise ValueError(f"Missing required field '{field}' in chunk {chunk.get('chunk_id')}")

    if not chunk["text"].strip():
        raise ValueError(f"Empty text detected in chunk {chunk.get('chunk_id')}")


def merge_chunks(datasets):

    merged = []
    seen_ids = set()

    for dataset_name, chunks in datasets.items():

        print(f"Processing {dataset_name}: {len(chunks)} chunks")

        for chunk in chunks:

            validate_chunk(chunk)

            cid = chunk["chunk_id"]

            if cid in seen_ids:
                raise ValueError(f"Duplicate chunk_id detected: {cid}")

            seen_ids.add(cid)
            merged.append(chunk)

    return merged


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main():

    print("\nLoading chunk datasets...\n")

    manual_chunks = load_json(MANUAL_PATH)
    recall_chunks = load_json(RECALL_PATH)
    warranty_chunks = load_json(WARRANTY_PATH)

    datasets = {
        "owner_manual": manual_chunks,
        "recall": recall_chunks,
        "warranty": warranty_chunks
    }

    merged_chunks = merge_chunks(datasets)

    # deterministic ordering
    merged_chunks = sorted(merged_chunks, key=lambda x: x["chunk_id"])

    print("\nMerged dataset size:", len(merged_chunks))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_chunks, f, indent=2, ensure_ascii=False)

    print("\nUnified dataset written to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()