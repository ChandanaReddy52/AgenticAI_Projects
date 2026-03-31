# chunk_owner_manual.py

import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "dataset v1" / "full_manual_clean.txt"
OUTPUT_PATH = BASE_DIR / "data" / "dataset v1" / "manual_chunks.json"

DOCUMENT_ID = "tucsonSep2020-Aug2022"
DOCUMENT_TYPE = "owner_manual"
MODEL = "Hyundai Tucson"
MODEL_YEAR_START = 2020
MODEL_YEAR_END = 2022
PUBLICATION_YEAR = 2020

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


def load_manual(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_by_pages(text):
    pages = {}
    pattern = r"===== PAGE (\d+) ====="
    splits = re.split(pattern, text)

    for i in range(1, len(splits), 2):
        page_number = int(splits[i])
        page_text = splits[i + 1].strip()
        pages[page_number] = page_text

    return pages


def build_chapter_text(pages):
    chapter_texts = {}

    for chapter, (start, end) in CHAPTER_RANGES.items():
        collected = []
        for p in range(start, end + 1):
            if p in pages:
                collected.append(pages[p])
        chapter_texts[chapter] = " ".join(collected).strip()

    return chapter_texts


def chunk_text(text, chapter_name):
    words = text.split()
    chunks = []

    start = 0
    chunk_id = 0

    while start < len(words):
        end = start + TARGET_MAX_WORDS
        chunk_words = words[start:end]

        if len(chunk_words) < TARGET_MIN_WORDS and end < len(words):
            end = min(len(words), start + TARGET_MIN_WORDS)
            chunk_words = words[start:end]

        chunk_text = " ".join(chunk_words)

        chunk_object = {
            "chunk_id": f"{DOCUMENT_TYPE}_{chapter_name}_{chunk_id}",
            "document_id": DOCUMENT_ID,
            "document_type": DOCUMENT_TYPE,

            "recall_id": None,
            "recall_role": None,
            "recall_severity": None,

            "warranty_type": None,
            "coverage_type": None,

            "component_categories": [],
            "model": MODEL,
            "model_year_start": MODEL_YEAR_START,
            "model_year_end": MODEL_YEAR_END,
            "publication_year": PUBLICATION_YEAR,

            "chapter": chapter_name,
            "section": None,

            "word_count": len(chunk_words),
            "text": chunk_text
        }

        chunks.append(chunk_object)

        chunk_id += 1
        start = end - OVERLAP_WORDS
        if start < 0:
            start = 0

    return chunks


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