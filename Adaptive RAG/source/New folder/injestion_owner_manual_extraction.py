import fitz
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_PATH = BASE_DIR / "data" / "dataset v1" / "tucsonSep2020-Aug2022.pdf"

START_PAGE = 32
END_PAGE = 40


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fix_hyphenation(text):
    return re.sub(r"(\w+)-\s+(\w+)", r"\1\2", text)


def remove_layout_noise(text):
    # Remove OTL codes
    text = re.sub(r"OTL\d+\w*", "", text)
    text = re.sub(r"/H", "", text)
    text = re.sub(r"\b\d+-\d+\b", "", text)

    # Remove repeating garbage prefix pattern
    text = re.sub(r"^!.*?\('", "", text)

    return text.strip()


def is_garbage(text):
    # if >60% characters are non-alphanumeric → likely encoded header
    if not text:
        return True
    alpha = len(re.findall(r"[A-Za-z]", text))
    return alpha < len(text) * 0.3


def extract_clean_pages(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)
    pages_text = {}

    for page_number in range(start_page, end_page + 1):
        page = doc[page_number - 1]
        page_dict = page.get_text("dict")

        page_lines = []

        for block in page_dict["blocks"]:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                spans = line["spans"]

                # Sort spans left to right to preserve first letters
                spans.sort(key=lambda s: s["bbox"][0])

                line_text = ""
                for span in spans:
                    text = span.get("text", "")
                    if not text:
                        continue
                    line_text += text

                line_text = clean_text(line_text)

                if not line_text:
                    continue

                if is_garbage(line_text):
                    continue

                page_lines.append(line_text)

        page_text = " ".join(page_lines)
        page_text = fix_hyphenation(page_text)
        page_text = remove_layout_noise(page_text)

        pages_text[page_number] = page_text

    doc.close()
    return pages_text


if __name__ == "__main__":
    pages = extract_clean_pages(PDF_PATH, START_PAGE, END_PAGE)

    for page_num, text in pages.items():
        print(f"\n===== PAGE {page_num} CLEAN TEXT =====\n")
        print(text[:1200])