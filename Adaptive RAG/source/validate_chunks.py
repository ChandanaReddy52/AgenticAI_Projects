#validate_chunks.py
import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "dataset v1"

FILES = [
    "manual_chunks.json",
    "recall_chunks.json",
    "warranty_chunks.json"
]

MAX_WORDS = 800
MIN_WORDS = 40


def load_chunks(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_chunks(chunks):

    issues = []

    texts = []
    ids = []

    for chunk in chunks:

        chunk_id = chunk.get("chunk_id")
        text = chunk.get("text", "")
        word_count = chunk.get("word_count", 0)

        ids.append(chunk_id)
        texts.append(text)

        # oversized chunk
        if word_count > MAX_WORDS:
            issues.append(f"Oversized chunk: {chunk_id} ({word_count} words)")

        # very small chunk
        if word_count < MIN_WORDS:
            issues.append(f"Small chunk: {chunk_id} ({word_count} words)")

        # missing metadata
        required = ["document_type", "section", "text"]

        for field in required:
            if field not in chunk or chunk[field] is None:
                issues.append(f"Missing metadata '{field}' in {chunk_id}")

        # garbage OCR detection
        if "TT TTe" in text or "eer r rrm" in text:
            issues.append(f"OCR artifact detected in {chunk_id}")

    # duplicate text detection
    duplicates = [item for item, count in Counter(texts).items() if count > 1]

    for dup in duplicates:
        issues.append("Duplicate chunk text detected")

    return issues


def main():

    all_issues = []

    for file in FILES:

        path = DATA_DIR / file
        chunks = load_chunks(path)

        print(f"\nChecking {file} ({len(chunks)} chunks)")

        issues = validate_chunks(chunks)

        if not issues:
            print("No issues detected")
        else:
            for issue in issues:
                print("⚠", issue)

        all_issues.extend(issues)

    print("\nSUMMARY")

    if not all_issues:
        print("Dataset is CLEAN — safe to freeze")
    else:
        print(f"{len(all_issues)} issues detected")


if __name__ == "__main__":
    main()