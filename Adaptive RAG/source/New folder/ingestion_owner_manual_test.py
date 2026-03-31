# ingestion_owner_manual_test.py

import fitz
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PDF_PATH = BASE_DIR / "data" / "dataset v1" / "tucsonSep2020-Aug2022.pdf"

START_PAGE = 32
END_PAGE = 40

BODY_FONT_SIZE = 12.8
SUBSECTION_THRESHOLD = 14.0


def is_valid_text(text):
    if not text:
        return False
    if len(re.findall(r"[A-Za-z]", text)) < 3:
        return False
    return True


def extract_structured_sections(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)

    sections = []
    current_subsection = None
    current_content = []

    for page_number in range(start_page, end_page + 1):
        page = doc[page_number - 1]
        page_dict = page.get_text("dict")

        for block in page_dict["blocks"]:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                line_text = ""
                max_size = 0

                for span in line["spans"]:
                    line_text += span["text"]
                    max_size = max(max_size, span["size"])

                clean = re.sub(r"\s+", " ", line_text).strip()

                if not is_valid_text(clean):
                    continue

                # Detect subsection heading
                if max_size >= SUBSECTION_THRESHOLD:
                    # Save previous subsection
                    if current_subsection:
                        sections.append({
                            "subsection": current_subsection,
                            "content": " ".join(current_content)
                        })
                        current_content = []

                    current_subsection = clean
                else:
                    if current_subsection:
                        current_content.append(clean)

    # Save last subsection
    if current_subsection and current_content:
        sections.append({
            "subsection": current_subsection,
            "content": " ".join(current_content)
        })

    doc.close()
    return sections


if __name__ == "__main__":
    structured_sections = extract_structured_sections(
        PDF_PATH,
        START_PAGE,
        END_PAGE
    )

    print("\n===== DETECTED SUBSECTIONS =====\n")

    for sec in structured_sections[:5]:
        print(f"\nSUBSECTION: {sec['subsection']}")
        print(f"CONTENT PREVIEW: {sec['content'][:300]}")
        print("-" * 80)