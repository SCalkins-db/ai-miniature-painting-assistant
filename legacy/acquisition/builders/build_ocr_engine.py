from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"


FILES = {
    ACQ_DIR / "ocr_cleaner.py": '''import re


class OCRCleaner:
    def clean_text(self, text):
        if not text:
            return ""

        text = text.replace("\\r", "\\n")
        text = re.sub(r"\\n{3,}", "\\n\\n", text)
        text = re.sub(r"[ \\t]+", " ", text)
        return text.strip()

    def clean_lines(self, text):
        cleaned = self.clean_text(text)
        return [line.strip() for line in cleaned.splitlines() if line.strip()]
''',

    ACQ_DIR / "ocr_engine.py": '''from pathlib import Path

from src.acquisition.ocr_cleaner import OCRCleaner


class OCREngine:
    def __init__(self):
        self.cleaner = OCRCleaner()

    def read_image(self, image_path):
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            from PIL import Image
            import pytesseract
        except ImportError as error:
            raise ImportError(
                "OCR dependencies missing. Install with: pip install pillow pytesseract"
            ) from error

        image = Image.open(image_path)
        raw_text = pytesseract.image_to_string(image)
        return self.cleaner.clean_text(raw_text)

    def read_lines(self, image_path):
        text = self.read_image(image_path)
        return self.cleaner.clean_lines(text)
''',

    ACQ_DIR / "ocr_parser.py": '''import re


class OCRParser:
    STEP_PATTERN = re.compile(r"step\\s+(\\d+)", re.IGNORECASE)

    PAINT_TYPES = [
        "Undercoat",
        "Primer",
        "Base",
        "Layer",
        "Shade",
        "Contrast",
        "Technical",
        "Dry",
        "Air",
        "Spray",
        "Wash",
        "Speedpaint",
        "Metallic",
        "Varnish",
    ]

    def detect_step_number(self, line):
        match = self.STEP_PATTERN.search(line)

        if not match:
            return None

        return int(match.group(1))

    def detect_paint_type(self, line):
        lowered = line.lower()

        for paint_type in self.PAINT_TYPES:
            if paint_type.lower() in lowered:
                return paint_type

        return ""

    def parse_lines(self, lines):
        parsed = []
        current_step = None

        for line in lines:
            step_number = self.detect_step_number(line)

            if step_number is not None:
                current_step = step_number
                parsed.append({
                    "kind": "step",
                    "step_order": current_step,
                    "text": line,
                })
                continue

            paint_type = self.detect_paint_type(line)

            parsed.append({
                "kind": "text",
                "step_order": current_step,
                "paint_type": paint_type,
                "text": line,
            })

        return parsed
''',

    ACQ_DIR / "ocr_validator.py": '''class OCRValidator:
    def validate_text(self, text):
        issues = []

        if not text or not text.strip():
            issues.append("OCR returned no text.")

        if text and len(text.strip()) < 10:
            issues.append("OCR text is suspiciously short.")

        return len(issues) == 0, issues

    def validate_lines(self, lines):
        issues = []

        if not lines:
            issues.append("No OCR lines found.")

        return len(issues) == 0, issues
''',

    DEBUG_DIR / "ocr_test.py": '''from pathlib import Path

from src.acquisition.ocr_engine import OCREngine
from src.acquisition.ocr_parser import OCRParser
from src.acquisition.ocr_validator import OCRValidator


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
    print("OCR TEST")
    print("=" * 60)

    image_path = find_first_image()

    if image_path is None:
        print("No image found to OCR.")
        print("Put screenshots into incoming/screenshots or run acquisition intake first.")
        return

    print(f"Testing image: {image_path}")

    engine = OCREngine()
    parser = OCRParser()
    validator = OCRValidator()

    try:
        text = engine.read_image(image_path)
    except Exception as error:
        print(f"OCR FAILED: {error}")
        return

    valid, issues = validator.validate_text(text)

    print("\\nOCR TEXT:")
    print("-" * 60)
    print(text[:2000])

    print("\\nVALIDATION:")
    print(f"Valid: {valid}")

    for issue in issues:
        print(f"- {issue}")

    lines = engine.cleaner.clean_lines(text)
    parsed = parser.parse_lines(lines)

    print("\\nPARSED LINES:")
    print("-" * 60)

    for item in parsed[:50]:
        print(item)

    print("=" * 60)
    print("OCR TEST COMPLETE")
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
    print("BUILDING OCR ENGINE")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Install Python OCR packages:")
    print("pip install pillow pytesseract")
    print("")
    print("Then run:")
    print("python -m src.debug.ocr_test")


if __name__ == "__main__":
    main()