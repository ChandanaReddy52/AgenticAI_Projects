# chunk_recall.py

import re
import json
from pathlib import Path
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "dataset v1"

TSB_PATH = DATA_DIR / "RCRIT-20V543-5288.pdf"  # 21-01-010H
NOTICE_1_PATH = DATA_DIR / "RCONL-20V543-0565.pdf"
NOTICE_2_PATH = DATA_DIR / "RCONL-20V543-2480.pdf"

OUTPUT_PATH = DATA_DIR / "recall_chunks.json"

DOCUMENT_TYPE = "recall"
DOCUMENT_ID = "recall_195_abs_fire"

MODEL = "Hyundai Tucson"
MODEL_YEAR_START = 2016
MODEL_YEAR_END = 2021
PUBLICATION_YEAR = 2021

TARGET_MAX_WORDS = 800
OVERLAP_WORDS = 120


# ---------------------------------------------------
# Utilities
# ---------------------------------------------------

def extract_pdf_text(path):
    reader = PdfReader(str(path))
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    return full_text


def hybrid_split(text):
    words = text.split()
    if len(words) <= TARGET_MAX_WORDS:
        return [text.strip()]

    chunks = []
    start = 0

    while start < len(words):
        end = start + TARGET_MAX_WORDS
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start = end - OVERLAP_WORDS

    return chunks


def build_chunk(text, chunk_id, section, recall_role):
    return {
        "chunk_id": chunk_id,
        "document_id": DOCUMENT_ID,
        "document_type": DOCUMENT_TYPE,
        "recall_id": "195",
        "recall_role": recall_role,
        "recall_severity": "high",
        "warranty_type": None,
        "coverage_type": None,
        "component_categories": ["ABS"],
        "model": MODEL,
        "model_year_start": MODEL_YEAR_START,
        "model_year_end": MODEL_YEAR_END,
        "publication_year": PUBLICATION_YEAR,
        "chapter": None,
        "section": section,
        "word_count": len(text.split()),
        "text": text.strip()
    }


# ---------------------------------------------------
# TSB Logical Segmentation
# ---------------------------------------------------

def chunk_tsb():
    text = extract_pdf_text(TSB_PATH)

    sections = {}

    # Logical splits
    desc_match = re.split(r"Parts Information:", text)
    sections["description"] = desc_match[0]

    parts_split = re.split(r"Warranty Information:", desc_match[1])
    sections["parts_and_warranty"] = parts_split[0]

    service_split = re.split(r"ABS/ESC Software Update Procedure", parts_split[1])
    service_text = service_split[0]
    software_text = service_split[1]

    # Split service procedure by step ranges
    step_blocks = re.split(r"\n\s*1\.", service_text)
    service_text_clean = "1." + step_blocks[1]

    steps = re.split(r"\n\s*(?=\d+\.)", service_text_clean)

    service_parts = []
    temp_block = ""
    count = 0

    for step in steps:
        temp_block += step + "\n"
        count += 1
        if count == 7:
            service_parts.append(temp_block)
            temp_block = ""
            count = 0

    if temp_block:
        service_parts.append(temp_block)

    sections["service_parts"] = service_parts
    sections["software"] = software_text

    chunks = []
    idx = 0

    # Description
    for block in hybrid_split(sections["description"]):
        chunks.append(build_chunk(
            block,
            f"recall_195_tsb_desc_{idx}",
            "recall_description",
            "tsb"
        ))
        idx += 1

    # Parts
    for block in hybrid_split(sections["parts_and_warranty"]):
        chunks.append(build_chunk(
            block,
            f"recall_195_tsb_parts_{idx}",
            "parts_and_warranty",
            "tsb"
        ))
        idx += 1

    # Service
    for i, part in enumerate(sections["service_parts"]):
        for block in hybrid_split(part):
            chunks.append(build_chunk(
                block,
                f"recall_195_tsb_service_{i}_{idx}",
                f"service_procedure_part{i+1}",
                "tsb"
            ))
            idx += 1

    # Software
    for block in hybrid_split(sections["software"]):
        chunks.append(build_chunk(
            block,
            f"recall_195_tsb_software_{idx}",
            "software_update_procedure",
            "tsb"
        ))
        idx += 1

    return chunks


# ---------------------------------------------------
# Customer Notice Chunking
# ---------------------------------------------------

def chunk_notice(path, suffix):
    text = extract_pdf_text(path)

    problem_split = re.split(r"What will Hyundai do\?", text)
    problem_text = problem_split[0]

    remedy_split = re.split(r"What should you do\?", problem_split[1])
    remedy_text = remedy_split[0]
    action_text = remedy_split[1]

    action_text = re.split(r"Window is", action_text)[0]
    action_text = re.split(r"IMPORTANT SAFETY RECALL", action_text)[0]

    chunks = []
    idx = 0

    for block in hybrid_split(problem_text):
        chunks.append(build_chunk(
            block,
            f"recall_195_notice_{suffix}_problem_{idx}",
            "owner_problem_description",
            "customer_notice"
        ))
        idx += 1

    for block in hybrid_split(remedy_text):
        chunks.append(build_chunk(
            block,
            f"recall_195_notice_{suffix}_remedy_{idx}",
            "owner_remedy_information",
            "customer_notice"
        ))
        idx += 1

    for block in hybrid_split(action_text):
        chunks.append(build_chunk(
            block,
            f"recall_195_notice_{suffix}_action_{idx}",
            "owner_action_required",
            "customer_notice"
        ))
        idx += 1

    return chunks


# ---------------------------------------------------
# Main
# ---------------------------------------------------

if __name__ == "__main__":

    print("Chunking TSB...")
    tsb_chunks = chunk_tsb()

    print("Chunking customer notices...")
    notice_1_chunks = chunk_notice(NOTICE_1_PATH, "1")
    notice_2_chunks = chunk_notice(NOTICE_2_PATH, "2")

    all_chunks = tsb_chunks + notice_1_chunks + notice_2_chunks

    print(f"Total recall chunks created: {len(all_chunks)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print("Saved to:", OUTPUT_PATH)