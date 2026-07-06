import csv
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
