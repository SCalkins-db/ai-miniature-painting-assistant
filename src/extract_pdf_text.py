from pathlib import Path
import fitz


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_DIR = PROJECT_ROOT / "data" / "source_documents" / "dakka"
OUTPUT_DIR = PROJECT_ROOT / "data" / "imports" / "extracted_text"


def extract_pdf(pdf_path: Path):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_txt = OUTPUT_DIR / f"{pdf_path.stem}.txt"

    doc = fitz.open(pdf_path)

    text_parts = []

    for page_number, page in enumerate(doc, start=1):
        text_parts.append(f"\n\n--- PAGE {page_number} ---\n")
        text_parts.append(page.get_text())

    output_txt.write_text("\n".join(text_parts), encoding="utf-8")

    print(f"Extracted: {pdf_path.name}")
    print(f"Saved to : {output_txt}")


def main():
    pdfs = sorted(PDF_DIR.glob("*.pdf"))

    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {PDF_DIR}")

    print("DAKKA PDF TEXT EXTRACTION")
    print("-------------------------")

    for pdf_path in pdfs:
        extract_pdf(pdf_path)

    print()
    print(f"Done. Extracted {len(pdfs)} PDF file(s).")


if __name__ == "__main__":
    main()