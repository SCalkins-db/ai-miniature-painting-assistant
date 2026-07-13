# Allow direct execution from project root or with python -m
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Allow direct execution from the project root, e.g. python src/debug/script.py
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from pathlib import Path
import fitz
from src.core.paths import PROJECT_ROOT, SRC_DIR, DATA_DIR, REGISTRIES_CSV_DIR, REGISTRIES_XLSX_DIR, MAPPINGS_DIR, REPORTS_DIR, SOURCE_DOCUMENTS_DIR, AUDIT_DIR, CSV_DIR, XLSX_DIR, SOURCE_DOCS_DIR



SOURCE_ROOT = SOURCE_DOCUMENTS_DIR
OUTPUT_ROOT = PROJECT_ROOT / "data" / "imports" / "extracted_text"

SUPPORTED_EXTENSIONS = {".pdf"}


def extract_pdf(pdf_path: Path, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)

    text_parts = []

    for page_number, page in enumerate(doc, start=1):
        text_parts.append(f"\n\n--- PAGE {page_number} ---\n")
        text_parts.append(page.get_text())

    output_path.write_text("\n".join(text_parts), encoding="utf-8")


def main():
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(f"Missing source folder: {SOURCE_ROOT}")

    pdf_files = sorted(
        path for path in SOURCE_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not pdf_files:
        print(f"No PDFs found in: {SOURCE_ROOT}")
        return

    print("UNIVERSAL PDF TEXT EXTRACTION")
    print("-----------------------------")
    print(f"Source root: {SOURCE_ROOT}")
    print(f"Output root: {OUTPUT_ROOT}")
    print()

    extracted_count = 0
    failed_count = 0

    for pdf_path in pdf_files:
        relative_path = pdf_path.relative_to(SOURCE_ROOT)
        output_path = OUTPUT_ROOT / relative_path.with_suffix(".txt")

        try:
            extract_pdf(pdf_path, output_path)
            extracted_count += 1
            print(f"Extracted: {relative_path}")
        except Exception as error:
            failed_count += 1
            print(f"FAILED: {relative_path}")
            print(f"  Error: {error}")

    print()
    print("EXTRACTION COMPLETE")
    print("-------------------")
    print(f"PDFs found: {len(pdf_files)}")
    print(f"Extracted successfully: {extracted_count}")
    print(f"Failed: {failed_count}")
    print(f"Output folder: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
