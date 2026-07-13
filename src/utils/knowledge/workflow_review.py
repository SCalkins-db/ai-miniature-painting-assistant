from pathlib import Path
import csv
from datetime import datetime

from src.knowledge.knowledge_paths import KNOWLEDGE_DIR


# ============================================================
# WORKFLOW REVIEW
# ============================================================
#
# PURPOSE
# -------
# Creates structured review tasks when the system cannot safely
# auto-import or auto-merge something.
#
# WHY THIS EXISTS
# ---------------
# The importer should not guess. If OCR is bad, title matching is
# weak, or two workflows are suspiciously similar, the system should
# put the item into review instead of corrupting the database.
#
# ============================================================


WORKFLOW_REVIEW_PATH = KNOWLEDGE_DIR / "workflow_review.csv"


HEADERS = [
    "Created_At",
    "Workflow_Key",
    "Issue_Type",
    "Issue_Detail",
    "Source_File",
    "Status",
]


class WorkflowReview:
    def __init__(self, path=WORKFLOW_REVIEW_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if self.path.exists():
            return

        with self.path.open("w", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=HEADERS).writeheader()

    def add(self, workflow_key, issue_type, issue_detail, source_file=""):
        with self.path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "Created_At": datetime.now().isoformat(timespec="seconds"),
                "Workflow_Key": workflow_key,
                "Issue_Type": issue_type,
                "Issue_Detail": issue_detail,
                "Source_File": source_file,
                "Status": "Open",
            })
