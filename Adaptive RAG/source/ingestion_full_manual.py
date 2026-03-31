# ingestion_full_manual_final.py

import fitz
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_PATH = BASE_DIR / "data" / "dataset v1" / "tucsonSep2020-Aug2022.pdf"

OUTPUT_PATH = BASE_DIR / "data" / "dataset v1" / "full_manual_clean.txt"

START_PAGE = 17
END_PAGE = 519


# -----------------------
# Cleaning Utilities
# -----------------------

def clean_text(text):
    text = text.replace("\x00", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fix_hyphenation(text):
    return re.sub(r"(\w+)-\s+(\w+)", r"\1\2", text)


def remove_layout_noise(text):
    text = re.sub(r"OTL\d+\w*", "", text)
    text = re.sub(r"/H", "", text)
    text = re.sub(r"\b\d+-\d+\b", "", text)
    return text.strip()


def is_empty_or_noise(text):
    if not text:
        return True

    # Remove lines with almost no letters
    alpha = len(re.findall(r"[A-Za-z]", text))
    if alpha < 3:
        return True

    return False


# -----------------------
# Core Extraction
# -----------------------

def extract_full_manual(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)

    all_pages = []

    for page_number in range(start_page, end_page + 1):
        page = doc[page_number - 1]
        page_dict = page.get_text("dict")

        page_lines = []

        for block in page_dict["blocks"]:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                spans = line["spans"]

                # CRITICAL: sort spans left → right (fix first letter cut issue)
                spans.sort(key=lambda s: s["bbox"][0])

                line_text = ""
                for span in spans:
                    text = span.get("text", "")
                    if text:
                        line_text += text

                line_text = clean_text(line_text)

                if is_empty_or_noise(line_text):
                    continue

                page_lines.append(line_text)

        # Merge page lines in extracted order
        page_text = " ".join(page_lines)

        page_text = fix_hyphenation(page_text)
        page_text = remove_layout_noise(page_text)

        all_pages.append(
            f"\n\n===== PAGE {page_number} =====\n\n{page_text}"
        )

    doc.close()

    full_text = "\n".join(all_pages)

    return full_text.strip()


# -----------------------
# Run
# -----------------------

if __name__ == "__main__":
    print("Extracting manual cleanly (stable mode)...")

    full_text = extract_full_manual(PDF_PATH, START_PAGE, END_PAGE)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(full_text)

    print("Done.")
    print("Saved to:", OUTPUT_PATH)