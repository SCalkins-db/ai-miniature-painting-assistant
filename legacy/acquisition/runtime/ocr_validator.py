class OCRValidator:
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
