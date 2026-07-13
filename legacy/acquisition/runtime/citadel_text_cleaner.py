import re


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

        if re.match(r"^\d{1,2}:\d{2}", lowered):
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
                title = re.sub(r"[^A-Za-z0-9 '\-]+", " ", title)
                title = re.sub(r"\s+", " ", title).strip()

                if title:
                    return title.title()

        for line in lines[:12]:
            if not self.is_phone_ui_junk(line) and "step" not in line.lower():
                return line.title()

        return "Unknown Workflow"
