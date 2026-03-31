import fitz
from pathlib import Path
import re
from bs4 import BeautifulSoup

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
    text = re.sub(r"OTL\d+\w*", "", text)
    text = re.sub(r"/H", "", text)
    text = re.sub(r"\b\d+-\d+\b", "", text)
    return text.strip()


def extract_clean_pages(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)
    pages_text = {}

    for page_number in range(start_page, end_page + 1):
        page = doc[page_number - 1]

        html = page.get_text("html")

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        text = clean_text(text)

        if len(text) < 20:
            pages_text[page_number] = ""
            continue

        text = fix_hyphenation(text)
        text = remove_layout_noise(text)

        pages_text[page_number] = text

    doc.close()
    return pages_text


if __name__ == "__main__":
    pages = extract_clean_pages(PDF_PATH, START_PAGE, END_PAGE)

    for page_num, text in pages.items():
        print(f"\n===== PAGE {page_num} CLEAN TEXT =====\n")
        print(text[:1200])