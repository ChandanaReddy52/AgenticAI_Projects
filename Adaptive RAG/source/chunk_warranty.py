import re
import json
from pathlib import Path
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "dataset v1"

EXTENDED_WARRANTY_PATH = DATA_DIR / "hyundai-comprehensive-ew-tandc.pdf"
BASIC_WARRANTY_PATH = DATA_DIR / "Hyundai-5-year-warranty-terms-and-conditions.pdf"

OUTPUT_PATH = DATA_DIR / "warranty_chunks.json"

MODEL = "Hyundai Tucson"
MODEL_YEAR_START = 2020
MODEL_YEAR_END = 2022
PUBLICATION_YEAR = 2020


# ---------------------------------------------------
# Utilities
# ---------------------------------------------------

def extract_pdf_text(path):
    reader = PdfReader(str(path))
    text = ""

    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"

    return text


def clean_text(text):

    text = re.sub(r"Page\s*\d+\s*of\s*\d+", "", text)
    text = re.sub(r"This document is protected.*", "", text)
    text = re.sub(r"\n+", "\n", text)

    return text.strip()


def build_chunk(text, chunk_id, document_id, section, warranty_type):

    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "document_type": "warranty",
        "recall_id": None,
        "recall_role": None,
        "recall_severity": None,
        "warranty_type": warranty_type,
        "coverage_type": None,
        "component_categories": [],
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
# Extended Warranty Chunking
# ---------------------------------------------------

def chunk_extended_warranty():

    text = extract_pdf_text(EXTENDED_WARRANTY_PATH)
    text = clean_text(text)

    sections = {}

    split1 = re.split(r"2\.\s*Extended Warranty Period", text)
    sections["extended_warranty_intro"] = split1[0]

    split2 = re.split(r"3\.\s*What is covered", split1[1])
    sections["extended_warranty_period"] = split2[0]

    split3 = re.split(r"4\.\s*What is not covered", split2[1])
    sections["coverage_scope"] = split3[0]

    split4 = re.split(r"5\s*Owner", split3[1])
    sections["coverage_exclusions"] = split4[0]

    split5 = re.split(r"HYUNDAI ROAD SIDE ASSISTANCE", split4[1])
    sections["owners_responsibilities"] = split5[0]

    rsa_split = split5[1]

    rsa_sections = re.split(r"\n\d+\.\s", rsa_split)

    sections["rsa_scope"] = rsa_sections[1]
    sections["rsa_services"] = rsa_sections[2]
    sections["rsa_customer_obligations"] = rsa_sections[3]
    sections["rsa_non_covered_events"] = rsa_sections[4]
    sections["rsa_constraints"] = rsa_sections[5]
    sections["rsa_disputes"] = rsa_sections[6]
    sections["rsa_liability"] = rsa_sections[7]

    chunks = []

    idx = 0

    for section, content in sections.items():

        if not content.strip():
            continue

        chunks.append(
            build_chunk(
                content,
                f"extended_warranty_{idx}",
                "hyundai_extended_warranty",
                section,
                "extended"
            )
        )

        idx += 1

    return chunks


# ---------------------------------------------------
# Basic Warranty Chunking
# ---------------------------------------------------

def chunk_basic_warranty():

    text = extract_pdf_text(BASIC_WARRANTY_PATH)
    text = clean_text(text)

    sections = {}

    split1 = re.split(r"(?i)scope\s+of\s+warranty", text)
    if len(split1) < 2:
        print("Warning: Scope of warranty not found")
        return []

    sections["warranty_definition"] = split1[0]

    split2 = re.split(r"(?i)general\s+exceptions", split1[1])
    sections["scope_of_warranty"] = split2[0]

    if len(split2) < 2:
        sections["general_exceptions"] = ""
        split3 = ["", ""]
    else:
        split3 = re.split(r"(?i)transfer\s+of\s+warranty", split2[1])
        sections["general_exceptions"] = split3[0]

    if len(split3) < 2:
        sections["transfer_of_warranty"] = ""
        split4 = ["", ""]
    else:
        split4 = re.split(r"(?i)supplementary\s+information", split3[1])
        sections["transfer_of_warranty"] = split4[0]

    if len(split4) < 2:
        sections["supplementary_information"] = ""
        split5 = ["", ""]
    else:
        split5 = re.split(r"(?i)standard\s+warranty\s+period", split4[1])
        sections["supplementary_information"] = split5[0]

    if len(split5) > 1:
        sections["standard_warranty_period"] = split5[1]
    else:
        sections["standard_warranty_period"] = ""

    chunks = []
    idx = 0

    for section, content in sections.items():

        if not content.strip():
            continue

        chunks.append(
            build_chunk(
                content,
                f"basic_warranty_{idx}",
                "hyundai_5year_warranty",
                section,
                "basic"
            )
        )

        idx += 1

    return chunks


# ---------------------------------------------------
# Main
# ---------------------------------------------------

if __name__ == "__main__":

    print("Chunking extended warranty...")
    extended_chunks = chunk_extended_warranty()

    print("Chunking basic warranty...")
    basic_chunks = chunk_basic_warranty()

    all_chunks = extended_chunks + basic_chunks

    print(f"Total warranty chunks created: {len(all_chunks)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print("Saved to:", OUTPUT_PATH)