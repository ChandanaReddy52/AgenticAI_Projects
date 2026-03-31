import fitz
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_PATH = BASE_DIR / "data" / "dataset v1" / "tucsonSep2020-Aug2022.pdf"

doc = fitz.open(PDF_PATH)
page = doc[32 - 1]

print("TEXT METHOD:")
print(page.get_text("text")[:500])

print("\nBLOCKS METHOD:")
print(page.get_text("blocks")[:3])

doc.close()