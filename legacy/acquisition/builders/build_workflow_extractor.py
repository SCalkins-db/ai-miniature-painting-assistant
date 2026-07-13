from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"


FILES = {
    ACQ_DIR / "paint_normalizer.py": '''import difflib
import pandas as pd

from src.database.database_paths import PROJECT_ROOT


REGISTRY_CSV_DIR = PROJECT_ROOT / "data" / "registries_csv"


class PaintNormalizer:
    def __init__(self):
        self.paint_lookup = self._load_paints()

    def _load_paints(self):
        paints = []

        if not REGISTRY_CSV_DIR.exists():
            return paints

        for csv_path in REGISTRY_CSV_DIR.glob("*.csv"):
            df = pd.read_csv(csv_path).fillna("")

            for _, row in df.iterrows():
                paint_name = row.get("Paint_Name", "")
                paint_id = row.get("Paint_ID", "")

                if not paint_name or not paint_id:
                    continue

                paints.append({
                    "paint_id": paint_id,
                    "paint_name": paint_name,
                    "company": row.get("Company", ""),
                    "product_line": row.get("Product_Line", ""),
                    "paint_type": row.get("Paint_Type", ""),
                })

        return paints

    def find_best_match(self, raw_name, cutoff=0.82):
        if not raw_name:
            return None

        names = [paint["paint_name"] for paint in self.paint_lookup]
        matches = difflib.get_close_matches(raw_name, names, n=1, cutoff=cutoff)

        if not matches:
            return None

        matched_name = matches[0]

        for paint in self.paint_lookup:
            if paint["paint_name"] == matched_name:
                return {
                    "raw_name": raw_name,
                    "paint_id": paint["paint_id"],
                    "paint_name": paint["paint_name"],
                    "company": paint["company"],
                    "product_line": paint["product_line"],
                    "paint_type": paint["paint_type"],
                    "confidence": "fuzzy",
                }

        return None
''',

    ACQ_DIR / "workflow_extractor.py": '''from pathlib import Path
import re
import pandas as pd

from src.acquisition.ocr_engine import OCREngine
from src.acquisition.ocr_parser import OCRParser
from src.acquisition.paint_normalizer import PaintNormalizer


WORKFLOW_COLUMNS = [
    "Workflow_ID",
    "Superfaction",
    "Faction",
    "Unit",
    "Model_Area",
    "Area_Order",
    "Step_Order",
    "Technique",
    "Paint_ID",
    "Paint_Name",
    "Purpose",
    "Optional",
    "Notes",
]


class WorkflowExtractor:
    def __init__(self):
        self.ocr = OCREngine()
        self.parser = OCRParser()
        self.normalizer = PaintNormalizer()

    def extract_from_image(self, image_path, workflow_id="UNKNOWN_WORKFLOW"):
        image_path = Path(image_path)

        text = self.ocr.read_image(image_path)
        lines = self.ocr.cleaner.clean_lines(text)
        parsed = self.parser.parse_lines(lines)

        title = self._guess_title(lines)
        rows = self._build_rows(parsed, workflow_id, title)

        return {
            "source_file": str(image_path),
            "workflow_id": workflow_id,
            "title": title,
            "raw_text": text,
            "lines": lines,
            "parsed": parsed,
            "workflow_df": pd.DataFrame(rows, columns=WORKFLOW_COLUMNS),
        }

    def _guess_title(self, lines):
        if not lines:
            return ""

        skip_terms = [
            "paint",
            "colour",
            "citadel",
            "step",
            "base",
            "layer",
            "shade",
            "undercoat",
        ]

        for line in lines[:10]:
            lowered = line.lower()

            if len(line) < 4:
                continue

            if any(term == lowered for term in skip_terms):
                continue

            if "step" in lowered:
                continue

            return line

        return lines[0]

    def _build_rows(self, parsed, workflow_id, title):
        rows = []
        current_step = 1
        area_order = 1
        model_area = "General"

        for item in parsed:
            text = item.get("text", "").strip()

            if not text:
                continue

            if item.get("kind") == "step":
                current_step = item.get("step_order") or current_step
                continue

            paint_type = item.get("paint_type", "")

            if not paint_type:
                continue

            paint_name = self._clean_paint_name(text, paint_type)

            if not paint_name:
                continue

            normalized = self.normalizer.find_best_match(paint_name)

            if normalized:
                paint_id = normalized["paint_id"]
                canonical_name = normalized["paint_name"]
                notes = f"Source: {title}; OCR raw: {text}; normalized from {paint_name}"
            else:
                paint_id = ""
                canonical_name = paint_name
                notes = f"Source: {title}; OCR raw: {text}; NEEDS PAINT MATCH REVIEW"

            rows.append({
                "Workflow_ID": workflow_id,
                "Superfaction": "",
                "Faction": "",
                "Unit": title,
                "Model_Area": model_area,
                "Area_Order": area_order,
                "Step_Order": current_step,
                "Technique": paint_type,
                "Paint_ID": paint_id,
                "Paint_Name": canonical_name,
                "Purpose": "",
                "Optional": "No",
                "Notes": notes,
            })

        return rows

    def _clean_paint_name(self, text, paint_type):
        cleaned = text.replace(paint_type, "")
        cleaned = re.sub(r"[^A-Za-z0-9 '\\-]+", " ", cleaned)
        cleaned = re.sub(r"\\s+", " ", cleaned).strip()

        bad_values = {
            "",
            "recommended",
            "air",
            "base",
            "layer",
            "shade",
            "undercoat",
            "technical",
        }

        if cleaned.lower() in bad_values:
            return ""

        return cleaned
''',

    ACQ_DIR / "workflow_csv_writer.py": '''from pathlib import Path
import re


def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


class WorkflowCSVWriter:
    def __init__(self, workflow_root="data/workflows/imported"):
        self.workflow_root = Path(workflow_root)
        self.workflow_root.mkdir(parents=True, exist_ok=True)

    def write(self, workflow_df, workflow_id, title=""):
        filename = f"{slugify(workflow_id)}.csv"
        path = self.workflow_root / filename

        workflow_df.to_csv(path, index=False)

        return path
''',

    DEBUG_DIR / "workflow_extractor_test.py": '''from pathlib import Path

from src.acquisition.workflow_extractor import WorkflowExtractor
from src.acquisition.workflow_csv_writer import WorkflowCSVWriter


IMAGE_DIRS = [
    Path("archive/screenshots"),
    Path("incoming/screenshots"),
    Path("incoming/extracted"),
]


def find_first_image():
    for image_dir in IMAGE_DIRS:
        if not image_dir.exists():
            continue

        for suffix in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            matches = list(image_dir.rglob(suffix))
            if matches:
                return matches[0]

    return None


def main():
    print("=" * 60)
    print("WORKFLOW EXTRACTOR TEST")
    print("=" * 60)

    image_path = find_first_image()

    if image_path is None:
        print("No image found.")
        return

    print(f"Testing image: {image_path}")

    extractor = WorkflowExtractor()
    writer = WorkflowCSVWriter()

    result = extractor.extract_from_image(
        image_path=image_path,
        workflow_id="OCR_TEST_WORKFLOW",
    )

    print("\\nTITLE:")
    print(result["title"])

    print("\\nRAW OCR TEXT:")
    print("-" * 60)
    print(result["raw_text"][:2000])

    print("\\nWORKFLOW DATAFRAME:")
    print("-" * 60)
    print(result["workflow_df"])

    output_path = writer.write(
        result["workflow_df"],
        result["workflow_id"],
        result["title"],
    )

    print("\\nWROTE:")
    print(output_path)

    print("=" * 60)
    print("WORKFLOW EXTRACTOR TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
'''
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING WORKFLOW EXTRACTOR")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run:")
    print("python -m src.debug.workflow_extractor_test")


if __name__ == "__main__":
    main()