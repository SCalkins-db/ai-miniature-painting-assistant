from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"


FILES = {
    ACQ_DIR / "workflow_resolver.py": '''import difflib
import re
import pandas as pd

from src.database.database_paths import PROJECT_ROOT


CATALOG_PATH = PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv"


class WorkflowResolver:
    def __init__(self, catalog_path=CATALOG_PATH):
        self.catalog_path = catalog_path
        self.catalog = self._load_catalog()

    def _load_catalog(self):
        if not self.catalog_path.exists():
            return pd.DataFrame()

        return pd.read_csv(self.catalog_path).dropna(how="all").fillna("")

    def normalize_text(self, value):
        value = str(value).lower()
        value = value.replace("sq", "squad")
        value = re.sub(r"[^a-z0-9]+", " ", value)
        value = re.sub(r"\\s+", " ", value).strip()
        return value

    def build_candidate_name(self, row):
        parts = [
            row.get("Faction", ""),
            row.get("Unit", ""),
            row.get("Character", ""),
        ]

        return " ".join([str(part) for part in parts if str(part).strip()])

    def resolve(self, raw_title="", source_path="", previous_title=""):
        if self.catalog.empty:
            return self._unknown("Catalog is empty")

        raw_norm = self.normalize_text(raw_title)
        source_norm = self.normalize_text(source_path)
        previous_norm = self.normalize_text(previous_title)

        candidates = []

        for _, row in self.catalog.iterrows():
            workflow_id = row.get("Workflow_ID", "")
            candidate_name = self.build_candidate_name(row)
            candidate_norm = self.normalize_text(candidate_name)

            score = 0
            reasons = []

            if raw_norm and raw_norm in candidate_norm:
                score += 70
                reasons.append("raw title prefix/substring match")

            if raw_norm and candidate_norm in raw_norm:
                score += 70
                reasons.append("candidate found in raw title")

            if raw_norm:
                fuzzy = difflib.SequenceMatcher(None, raw_norm, candidate_norm).ratio()
                score += int(fuzzy * 40)
                reasons.append(f"fuzzy raw title score {fuzzy:.2f}")

            if source_norm and row.get("Faction", "").lower() in source_norm:
                score += 10
                reasons.append("faction found in source path")

            if source_norm and row.get("Unit", "").lower() in source_norm:
                score += 15
                reasons.append("unit found in source path")

            if previous_norm and previous_norm in candidate_norm:
                score += 10
                reasons.append("previous title context")

            candidates.append({
                "workflow_id": workflow_id,
                "resolved_title": candidate_name,
                "score": score,
                "reasons": "; ".join(reasons),
            })

        candidates = sorted(candidates, key=lambda item: item["score"], reverse=True)

        best = candidates[0]

        confidence = self._score_to_confidence(best["score"])

        if best["score"] < 45:
            return {
                "workflow_id": "",
                "raw_title": raw_title,
                "resolved_title": "",
                "confidence": confidence,
                "score": best["score"],
                "status": "Needs Review",
                "reason": f"Low score. Best candidate: {best}",
            }

        return {
            "workflow_id": best["workflow_id"],
            "raw_title": raw_title,
            "resolved_title": best["resolved_title"],
            "confidence": confidence,
            "score": best["score"],
            "status": "Resolved" if best["score"] >= 70 else "Needs Review",
            "reason": best["reasons"],
        }

    def _score_to_confidence(self, score):
        if score >= 90:
            return "High"
        if score >= 70:
            return "Medium"
        if score >= 45:
            return "Low"
        return "Very Low"

    def _unknown(self, reason):
        return {
            "workflow_id": "",
            "raw_title": "",
            "resolved_title": "",
            "confidence": "Very Low",
            "score": 0,
            "status": "Needs Review",
            "reason": reason,
        }
''',

    DEBUG_DIR / "workflow_resolver_test.py": '''from src.acquisition.workflow_resolver import WorkflowResolver


TEST_CASES = [
    {
        "raw_title": "White Scars Tactical Sq",
        "source_path": "archive/screenshots/imperials/image0.png",
    },
    {
        "raw_title": "Ultramarines Assault Inter...",
        "source_path": "archive/screenshots/imperium/ultramarines/image10.png",
    },
    {
        "raw_title": "Space Wolves Redemptor",
        "source_path": "archive/screenshots/space_wolves/image20.png",
    },
]


def main():
    print("=" * 60)
    print("WORKFLOW RESOLVER TEST")
    print("=" * 60)

    resolver = WorkflowResolver()

    print(f"Catalog rows: {len(resolver.catalog)}")

    for case in TEST_CASES:
        print("\\nRAW TITLE:")
        print(case["raw_title"])

        result = resolver.resolve(
            raw_title=case["raw_title"],
            source_path=case["source_path"],
        )

        print("RESULT:")
        for key, value in result.items():
            print(f"{key}: {value}")

    print("=" * 60)
    print("WORKFLOW RESOLVER TEST COMPLETE")
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
    print("BUILDING WORKFLOW RESOLVER")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run:")
    print("python -m src.debug.workflow_resolver_test")


if __name__ == "__main__":
    main()