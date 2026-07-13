from pathlib import Path

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

            TESSERACT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

            if TESSERACT_PATH.exists():
                pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)
            else:
                raise FileNotFoundError(
                    f"Tesseract executable not found: {TESSERACT_PATH}"
                )

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