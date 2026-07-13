from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"


FILES = {
    ACQ_DIR / "citadel_text_cleaner.py": '''import re


class CitadelTextCleaner:
    JUNK_TERMS = [
        "projects",
        "profile",
        "paint",
        "colour",
        "citadel",
        "download",
        "share",
    ]

    def clean_lines(self, lines):
        cleaned = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            if self.is_phone_ui_junk(line):
                continue

            cleaned.append(line)

        return cleaned

    def is_phone_ui_junk(self, line):
        lowered = line.lower().strip()

        if re.match(r"^\\d{1,2}:\\d{2}", lowered):
            return True

        if lowered in self.JUNK_TERMS:
            return True

        if lowered in ["s", "c", "6", "©"]:
            return True

        if "projects profile" in lowered:
            return True

        return False

    def extract_title(self, lines):
        for line in lines:
            if "<" in line:
                title = line.replace("<", "")
                title = title.replace("©", "")
                title = title.replace("...", "")
                title = title.replace("$0", "SQ")
                title = re.sub(r"[^A-Za-z0-9 '\\-]+", " ", title)
                title = re.sub(r"\\s+", " ", title).strip()

                if title:
                    return title.title()

        for line in lines[:12]:
            if not self.is_phone_ui_junk(line) and "step" not in line.lower():
                return line.title()

        return "Unknown Workflow"
''',

    ACQ_DIR / "workflow_extractor.py": '''from pathlib import Path
import re
import pandas as pd

from src.acquisition.ocr_engine import OCREngine
from src.acquisition.ocr_parser import OCRParser
from src.acquisition.paint_normalizer import PaintNormalizer
from src.acquisition.citadel_text_cleaner import CitadelTextCleaner


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
        self.cleaner = CitadelTextCleaner()

    def extract_from_image(self, image_path, workflow_id="UNKNOWN_WORKFLOW"):
        image_path = Path(image_path)

        text = self.ocr.read_image(image_path)
        raw_lines = self.ocr.cleaner.clean_lines(text)
        lines = self.cleaner.clean_lines(raw_lines)

        title = self.cleaner.extract_title(raw_lines)
        parsed = self.parser.parse_lines(lines)
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

    def _build_rows(self, parsed, workflow_id, title):
        rows = []
        current_step = 1
        area_order = 1
        model_area = "General"

        pending_paint_name = ""

        for item in parsed:
            text = item.get("text", "").strip()

            if not text:
                continue

            if item.get("kind") == "step":
                current_step = item.get("step_order") or current_step
                pending_paint_name = ""
                continue

            paint_type = item.get("paint_type", "")

            if paint_type:
                paint_name = pending_paint_name or self._clean_paint_name(text, paint_type)

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
                    "Purpose": self._extract_purpose(text),
                    "Optional": "No",
                    "Notes": notes,
                })

                pending_paint_name = ""
                continue

            if self._looks_like_paint_name(text):
                pending_paint_name = self._clean_possible_paint_name(text)

        return rows

    def _looks_like_paint_name(self, text):
        lowered = text.lower()

        if "step" in lowered:
            return False

        if len(text) < 3:
            return False

        if any(word in lowered for word in ["all areas", "areas", "basecoat", "shade", "layer", "undercoat"]):
            return False

        return bool(re.search(r"[A-Za-z]", text))

    def _clean_possible_paint_name(self, text):
        text = re.sub(r"\\d+\\)?", "", text)
        text = re.sub(r"[^A-Za-z0-9 '\\-]+", " ", text)
        text = re.sub(r"\\s+", " ", text).strip()
        return text

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

    def _extract_purpose(self, text):
        if "@" in text:
            return text.split("@", 1)[-1].strip()

        if "O" in text:
            parts = text.split("O", 1)
            if len(parts) > 1:
                return parts[-1].strip()

        return ""
'''
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING CITADEL CLEANER V1")
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