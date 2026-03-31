# chunck_manual.py

import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "dataset v1" / "full_manual_clean.txt"
OUTPUT_PATH = BASE_DIR / "data" / "dataset v1" / "manual_chunks.json"

# ---------------------------------------------------
# Chapter Page Ranges (Finalized)
# ---------------------------------------------------

CHAPTER_RANGES = {
    "warranty_policy": (17, 24),
    "safety_system": (32, 93),
    "convenient_features": (94, 239),
    "driving": (293, 363),
    "emergency": (364, 392),
    "maintenance": (393, 506),
    "specifications": (507, 519),
}

TARGET_MIN_WORDS = 400
TARGET_MAX_WORDS = 800
OVERLAP_WORDS = 120


# ---------------------------------------------------
# Utilities
# ---------------------------------------------------

def load_manual(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_by_pages(text):
    """
    Returns dict: {page_number: page_text}
    """
    pages = {}
    pattern = r"===== PAGE (\d+) ====="
    splits = re.split(pattern, text)

    # splits structure:
    # [before, page_number, page_text, page_number, page_text, ...]

    for i in range(1, len(splits), 2):
        page_number = int(splits[i])
        page_text = splits[i + 1].strip()
        pages[page_number] = page_text

    return pages


def build_chapter_text(pages):
    """
    Returns dict: {chapter_name: full_text}
    """
    chapter_texts = {}

    for chapter, (start, end) in CHAPTER_RANGES.items():
        collected = []
        for p in range(start, end + 1):
            if p in pages:
                collected.append(pages[p])
        chapter_texts[chapter] = " ".join(collected).strip()

    return chapter_texts


def chunk_text(text, chapter_name):
    """
    Chunk by word window with overlap.
    Keeps semantic continuity.
    """
    words = text.split()
    chunks = []

    start = 0
    chunk_id = 0

    while start < len(words):
        end = start + TARGET_MAX_WORDS
        chunk_words = words[start:end]

        if len(chunk_words) < TARGET_MIN_WORDS and end < len(words):
            # extend slightly if too small
            end = min(len(words), start + TARGET_MIN_WORDS)
            chunk_words = words[start:end]

        chunk_text = " ".join(chunk_words)

        chunks.append({
            "chunk_id": f"{chapter_name}_{chunk_id}",
            "chapter": chapter_name,
            "word_count": len(chunk_words),
            "text": chunk_text
        })

        chunk_id += 1
        start = end - OVERLAP_WORDS

        if start < 0:
            start = 0

    return chunks


# ---------------------------------------------------
# Main Pipeline
# ---------------------------------------------------

if __name__ == "__main__":
    print("Loading clean manual...")
    full_text = load_manual(INPUT_PATH)

    print("Splitting into pages...")
    pages = split_by_pages(full_text)

    print("Building chapter texts...")
    chapter_texts = build_chapter_text(pages)

    print("Chunking chapters...")
    all_chunks = []

    for chapter, text in chapter_texts.items():
        if not text:
            continue
        chapter_chunks = chunk_text(text, chapter)
        all_chunks.extend(chapter_chunks)

    print(f"Total chunks created: {len(all_chunks)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print("Saved to:", OUTPUT_PATH)