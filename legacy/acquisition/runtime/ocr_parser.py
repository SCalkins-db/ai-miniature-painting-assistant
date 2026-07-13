import re


class OCRParser:
    STEP_PATTERN = re.compile(r"step\s+(\d+)", re.IGNORECASE)

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
