import difflib
import re


def normalize_title(value):
    value = str(value).lower()
    value = value.replace("sq", "squad")
    value = value.replace("...", "")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


class WorkflowSimilarity:
    def score(self, title_a, title_b):
        norm_a = normalize_title(title_a)
        norm_b = normalize_title(title_b)

        if not norm_a or not norm_b:
            return 0

        if norm_a == norm_b:
            return 100

        if norm_a in norm_b or norm_b in norm_a:
            return 85

        return int(difflib.SequenceMatcher(None, norm_a, norm_b).ratio() * 100)
