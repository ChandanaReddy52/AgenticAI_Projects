#ingestion_structured_manual.py
import fitz
import re
import json
from pathlib import Path

# ---------------------------------
# CONFIG
# ---------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_PATH = BASE_DIR / "data" / "dataset v1" / "tucsonSep2020-Aug2022.pdf"
OUTPUT_PATH = BASE_DIR / "data" / "dataset v1" / "manual_chunks.json"

CHAPTERS = {
    "warranty_policy": (17, 24),
    "safety_system": (32, 93),
    "convenient_features": (94, 239),
    "driving": (293, 363),
    "emergency": (364, 392),
    "maintenance": (393, 506),
    "specifications": (507, 519),
}

MIN_WORDS = 300
MAX_WORDS = 800
OVERLAP_WORDS = 100


# ---------------------------------
# CLEANING UTILITIES
# ---------------------------------

def clean_line(text):
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def remove_noise(text):
    text = re.sub(r"\b[A-Z0-9]{5,}\b", "", text)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_garbage(text):
    if not text:
        return True
    alpha = len(re.findall(r"[A-Za-z]", text))
    return alpha < len(text) * 0.3


# ---------------------------------
# HEADER DETECTION
# ---------------------------------

def is_section_header(line):
    line = line.strip()

    if len(line) < 3:
        return False

    # ALL CAPS short lines
    if line.isupper() and len(line.split()) <= 12:
        return True

    # Numbered headings
    if re.match(r"^\d+\.", line):
        return True

    return False


# ---------------------------------
# PDF EXTRACTION PER CHAPTER
# ---------------------------------

def extract_chapter_text(pdf_path, start_page, end_page):

    doc = fitz.open(pdf_path)
    lines = []

    for page_number in range(start_page, end_page + 1):
        page = doc[page_number - 1]
        page_dict = page.get_text("dict")

        for block in page_dict["blocks"]:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                spans = line["spans"]
                spans.sort(key=lambda s: s["bbox"][0])

                line_text = ""
                for span in spans:
                    text = span.get("text", "")
                    line_text += text

                line_text = clean_line(line_text)

                if is_garbage(line_text):
                    continue

                lines.append(line_text)

    doc.close()

    full_text = " ".join(lines)
    full_text = remove_noise(full_text)

    return full_text


# ---------------------------------
# SEMANTIC SECTION SPLITTING
# ---------------------------------

def split_into_sections(text):

    sentences = re.split(r'(?<=\.)\s+', text)

    sections = []
    current_header = None
    current_text = []

    for sentence in sentences:
        sentence = sentence.strip()

        if is_section_header(sentence):

            if current_header and current_text:
                sections.append({
                    "header": current_header,
                    "text": " ".join(current_text)
                })
                current_text = []

            current_header = sentence

        else:
            current_text.append(sentence)

    if current_header and current_text:
        sections.append({
            "header": current_header,
            "text": " ".join(current_text)
        })

    return sections


# ---------------------------------
# CHUNKING WITH OVERLAP
# ---------------------------------

def split_large_section(text):

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):

        end = min(start + MAX_WORDS, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        if end == len(words):
            break

        start += MAX_WORDS - OVERLAP_WORDS

    return chunks


# ---------------------------------
# BUILD FINAL STRUCTURED CHUNKS
# ---------------------------------

def build_manual_chunks():

    final_chunks = []

    for chapter_name, (start_page, end_page) in CHAPTERS.items():

        print(f"Extracting {chapter_name} ({start_page}-{end_page})")

        chapter_text = extract_chapter_text(PDF_PATH, start_page, end_page)
        sections = split_into_sections(chapter_text)

        for sec in sections:

            word_count = len(sec["text"].split())

            base_metadata = {
                "chapter": chapter_name,
                "section": sec["header"],
                "page_start": start_page,
                "page_end": end_page
            }

            if word_count <= MAX_WORDS:

                chunk = base_metadata.copy()
                chunk["text"] = sec["text"]
                chunk["word_count"] = word_count
                final_chunks.append(chunk)

            else:

                split_chunks = split_large_section(sec["text"])

                for chunk_text in split_chunks:

                    chunk = base_metadata.copy()
                    chunk["text"] = chunk_text
                    chunk["word_count"] = len(chunk_text.split())
                    final_chunks.append(chunk)

    return final_chunks


# ---------------------------------
# MAIN
# ---------------------------------

if __name__ == "__main__":

    print("Building structured manual chunks...")

    chunks = build_manual_chunks()

    print(f"\nTotal chunks created: {len(chunks)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    print("Saved to:", OUTPUT_PATH)

    print("\nSample chunk:")
    print("Chapter:", chunks[0]["chapter"])
    print("Section:", chunks[0]["section"])
    print("Words:", chunks[0]["word_count"])
    print("Preview:", chunks[0]["text"][:400])