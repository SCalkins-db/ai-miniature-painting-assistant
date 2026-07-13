import re


class OCRCleaner:
    def clean_text(self, text):
        if not text:
            return ""

        text = text.replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def clean_lines(self, text):
        cleaned = self.clean_text(text)
        return [line.strip() for line in cleaned.splitlines() if line.strip()]
