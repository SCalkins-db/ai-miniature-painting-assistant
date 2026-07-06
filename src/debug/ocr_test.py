from pathlib import Path

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

    print("\nOCR TEXT:")
    print("-" * 60)
    print(text[:2000])

    print("\nVALIDATION:")
    print(f"Valid: {valid}")

    for issue in issues:
        print(f"- {issue}")

    lines = engine.cleaner.clean_lines(text)
    parsed = parser.parse_lines(lines)

    print("\nPARSED LINES:")
    print("-" * 60)

    for item in parsed[:50]:
        print(item)

    print("=" * 60)
    print("OCR TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
