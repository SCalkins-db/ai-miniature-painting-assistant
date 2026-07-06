from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "src" / "knowledge"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"

FOLDERS = [
    PROJECT_ROOT / "data" / "knowledge",
    PROJECT_ROOT / "review",
]

FILES = {
    KNOWLEDGE_DIR / "__init__.py": "",

    KNOWLEDGE_DIR / "knowledge_paths.py": r'''from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"

WORKFLOW_CANDIDATES_PATH = KNOWLEDGE_DIR / "workflow_candidates.csv"
WORKFLOW_MERGE_LOG_PATH = KNOWLEDGE_DIR / "workflow_merge_log.csv"
''',

    KNOWLEDGE_DIR / "confidence_engine.py": r'''class ConfidenceEngine:
    def title_confidence(self, raw_title, resolved_title, score):
        if not raw_title:
            return "Very Low"

        if score >= 90:
            return "High"

        if score >= 70:
            return "Medium"

        if score >= 45:
            return "Low"

        return "Very Low"

    def import_status(self, confidence):
        if confidence == "High":
            return "Auto Import"

        if confidence == "Medium":
            return "Needs Quick Review"

        return "Manual Review"
''',

    KNOWLEDGE_DIR / "workflow_similarity.py": r'''import difflib
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
''',

    KNOWLEDGE_DIR / "workflow_catalog_builder.py": r'''import csv
from datetime import datetime
from pathlib import Path

from src.knowledge.knowledge_paths import WORKFLOW_CANDIDATES_PATH, KNOWLEDGE_DIR
from src.knowledge.workflow_similarity import WorkflowSimilarity
from src.knowledge.confidence_engine import ConfidenceEngine


HEADERS = [
    "Created_At",
    "Raw_Title",
    "Resolved_Title",
    "Workflow_ID",
    "Source_File",
    "Confidence",
    "Score",
    "Status",
    "Reason",
]


class WorkflowCatalogBuilder:
    def __init__(self):
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        self.similarity = WorkflowSimilarity()
        self.confidence_engine = ConfidenceEngine()
        self._ensure_file()

    def _ensure_file(self):
        if WORKFLOW_CANDIDATES_PATH.exists():
            return

        with WORKFLOW_CANDIDATES_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()

    def load_candidates(self):
        rows = []

        with WORKFLOW_CANDIDATES_PATH.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)

        return rows

    def find_existing_candidate(self, raw_title):
        existing = self.load_candidates()

        best = None
        best_score = 0

        for row in existing:
            candidate_title = row.get("Raw_Title", "") or row.get("Resolved_Title", "")
            score = self.similarity.score(raw_title, candidate_title)

            if score > best_score:
                best = row
                best_score = score

        if best_score >= 85:
            return best, best_score

        return None, best_score

    def add_or_merge_candidate(
        self,
        raw_title,
        resolved_title="",
        workflow_id="",
        source_file="",
        resolver_score=0,
        reason="",
    ):
        existing, similarity_score = self.find_existing_candidate(raw_title)

        if existing:
            return {
                "action": "Duplicate Candidate",
                "raw_title": raw_title,
                "matched_title": existing.get("Raw_Title", ""),
                "similarity_score": similarity_score,
                "status": "Skipped",
            }

        confidence = self.confidence_engine.title_confidence(
            raw_title=raw_title,
            resolved_title=resolved_title,
            score=resolver_score,
        )

        status = self.confidence_engine.import_status(confidence)

        with WORKFLOW_CANDIDATES_PATH.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "Created_At": datetime.now().isoformat(timespec="seconds"),
                "Raw_Title": raw_title,
                "Resolved_Title": resolved_title,
                "Workflow_ID": workflow_id,
                "Source_File": source_file,
                "Confidence": confidence,
                "Score": resolver_score,
                "Status": status,
                "Reason": reason,
            })

        return {
            "action": "Added Candidate",
            "raw_title": raw_title,
            "resolved_title": resolved_title,
            "workflow_id": workflow_id,
            "confidence": confidence,
            "status": status,
        }
''',

    KNOWLEDGE_DIR / "knowledge_manager.py": r'''from src.knowledge.workflow_catalog_builder import WorkflowCatalogBuilder


class KnowledgeManager:
    def __init__(self):
        self.catalog_builder = WorkflowCatalogBuilder()

    def process_extraction_result(self, extraction_result):
        raw_title = extraction_result.get("raw_title", "")
        resolved_title = extraction_result.get("resolved_title", "")
        workflow_id = extraction_result.get("workflow_id", "")
        source_file = extraction_result.get("source_file", "")
        score = extraction_result.get("score", 0)
        reason = extraction_result.get("reason", "")

        return self.catalog_builder.add_or_merge_candidate(
            raw_title=raw_title,
            resolved_title=resolved_title,
            workflow_id=workflow_id,
            source_file=source_file,
            resolver_score=score,
            reason=reason,
        )
''',

    SCRIPTS_DIR / "build_knowledge_from_acquisition_report.py": r'''from pathlib import Path
import pandas as pd

from src.knowledge.knowledge_manager import KnowledgeManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "acquisition_pipeline_report.csv"


def main():
    print("=" * 60)
    print("BUILDING KNOWLEDGE FROM ACQUISITION REPORT")
    print("=" * 60)

    if not REPORT_PATH.exists():
        print(f"Missing report: {REPORT_PATH}")
        print("Run acquisition pipeline or acquisition pipeline test first.")
        return

    df = pd.read_csv(REPORT_PATH).fillna("")
    manager = KnowledgeManager()

    added = 0
    duplicates = 0

    for _, row in df.iterrows():
        result = manager.process_extraction_result({
            "raw_title": row.get("raw_title", ""),
            "resolved_title": row.get("resolved_title", ""),
            "workflow_id": row.get("workflow_id", ""),
            "source_file": row.get("source_file", ""),
            "score": int(row.get("score", 0) or 0),
            "reason": row.get("resolver_status", ""),
        })

        if result["action"] == "Added Candidate":
            added += 1
        else:
            duplicates += 1

    print(f"Rows processed: {len(df)}")
    print(f"Candidates added: {added}")
    print(f"Duplicates skipped: {duplicates}")
    print("=" * 60)
    print("Wrote:")
    print("data/knowledge/workflow_candidates.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DEBUG_DIR / "knowledge_test.py": r'''from src.knowledge.knowledge_manager import KnowledgeManager


def main():
    print("=" * 60)
    print("KNOWLEDGE ENGINE TEST")
    print("=" * 60)

    manager = KnowledgeManager()

    samples = [
        {
            "raw_title": "White Scars Tactical Sq",
            "resolved_title": "",
            "workflow_id": "UNRESOLVED_IMAGE0",
            "source_file": "archive/screenshots/image0.png",
            "score": 9,
            "reason": "Needs Review",
        },
        {
            "raw_title": "White Scars Tactical Squad",
            "resolved_title": "White Scars Tactical Squad",
            "workflow_id": "GW_WHITE_SCARS_TACTICAL_SQUAD",
            "source_file": "archive/screenshots/image999.png",
            "score": 95,
            "reason": "Full title found later",
        },
    ]

    for sample in samples:
        result = manager.process_extraction_result(sample)
        print(result)

    print("=" * 60)
    print("KNOWLEDGE ENGINE TEST COMPLETE")
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
    print("BUILDING KNOWLEDGE ENGINE V1")
    print("=" * 60)

    for folder in FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"ENSURED DIR: {folder}")

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run:")
    print("python -m src.debug.knowledge_test")
    print("")
    print("If you have acquisition_pipeline_report.csv, run:")
    print("python -m src.scripts.build_knowledge_from_acquisition_report")


if __name__ == "__main__":
    main()