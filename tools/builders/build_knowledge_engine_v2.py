from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "src" / "knowledge"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"

FOLDERS = [
    PROJECT_ROOT / "data" / "knowledge",
    PROJECT_ROOT / "review",
]


FILES = {
    KNOWLEDGE_DIR / "workflow_state.py": r'''from pathlib import Path
import csv
from datetime import datetime

from src.knowledge.knowledge_paths import KNOWLEDGE_DIR


# ============================================================
# WORKFLOW STATE
# ============================================================
#
# PURPOSE
# -------
# Tracks the current known state of each workflow candidate.
#
# WHY THIS EXISTS
# ---------------
# OCR and screenshot imports are imperfect. The same workflow may
# appear several times with partial names, better names, better
# screenshots, or improved extracted data.
#
# This file acts like the memory ledger for workflows.
#
# It helps prevent the system from treating every screenshot as
# a brand-new workflow.
#
# ============================================================


WORKFLOW_STATE_PATH = KNOWLEDGE_DIR / "workflow_state.csv"


HEADERS = [
    "Workflow_Key",
    "Best_Title",
    "Best_Workflow_ID",
    "Best_Source_File",
    "Confidence",
    "Status",
    "Times_Seen",
    "First_Seen",
    "Last_Seen",
    "Notes",
]


class WorkflowState:
    def __init__(self, path=WORKFLOW_STATE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if self.path.exists():
            return

        with self.path.open("w", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=HEADERS).writeheader()

    def load(self):
        with self.path.open("r", newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    def save(self, rows):
        with self.path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(rows)

    def upsert(self, workflow_key, title, workflow_id="", source_file="", confidence="Very Low", status="Needs Review", notes=""):
        now = datetime.now().isoformat(timespec="seconds")
        rows = self.load()

        for row in rows:
            if row["Workflow_Key"] == workflow_key:
                row["Times_Seen"] = str(int(row.get("Times_Seen", "0") or 0) + 1)
                row["Last_Seen"] = now

                # Keep better information when a later screenshot gives us a
                # better title, source file, or confidence.
                if title and len(title) > len(row.get("Best_Title", "")):
                    row["Best_Title"] = title

                if workflow_id and not row.get("Best_Workflow_ID"):
                    row["Best_Workflow_ID"] = workflow_id

                if source_file:
                    row["Best_Source_File"] = source_file

                row["Confidence"] = confidence or row.get("Confidence", "")
                row["Status"] = status or row.get("Status", "")
                row["Notes"] = notes or row.get("Notes", "")

                self.save(rows)
                return row

        new_row = {
            "Workflow_Key": workflow_key,
            "Best_Title": title,
            "Best_Workflow_ID": workflow_id,
            "Best_Source_File": source_file,
            "Confidence": confidence,
            "Status": status,
            "Times_Seen": "1",
            "First_Seen": now,
            "Last_Seen": now,
            "Notes": notes,
        }

        rows.append(new_row)
        self.save(rows)

        return new_row
''',

    KNOWLEDGE_DIR / "workflow_history.py": r'''from pathlib import Path
import csv
from datetime import datetime

from src.knowledge.knowledge_paths import KNOWLEDGE_DIR


# ============================================================
# WORKFLOW HISTORY
# ============================================================
#
# PURPOSE
# -------
# Records every meaningful workflow decision the knowledge engine
# makes.
#
# WHY THIS EXISTS
# ---------------
# If a workflow title changes from "White Scars Tactical Sq" to
# "White Scars Tactical Squad", we do not want to lose the old
# evidence.
#
# This history log helps debug bad merges, bad OCR reads, and
# duplicate-prevention decisions later.
#
# ============================================================


WORKFLOW_HISTORY_PATH = KNOWLEDGE_DIR / "workflow_history.csv"


HEADERS = [
    "Created_At",
    "Workflow_Key",
    "Event_Type",
    "Old_Value",
    "New_Value",
    "Source_File",
    "Notes",
]


class WorkflowHistory:
    def __init__(self, path=WORKFLOW_HISTORY_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if self.path.exists():
            return

        with self.path.open("w", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=HEADERS).writeheader()

    def record(self, workflow_key, event_type, old_value="", new_value="", source_file="", notes=""):
        with self.path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "Created_At": datetime.now().isoformat(timespec="seconds"),
                "Workflow_Key": workflow_key,
                "Event_Type": event_type,
                "Old_Value": old_value,
                "New_Value": new_value,
                "Source_File": source_file,
                "Notes": notes,
            })
''',

    KNOWLEDGE_DIR / "workflow_review.py": r'''from pathlib import Path
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
''',

    KNOWLEDGE_DIR / "workflow_merge_engine.py": r'''from src.knowledge.workflow_similarity import WorkflowSimilarity, normalize_title


# ============================================================
# WORKFLOW MERGE ENGINE
# ============================================================
#
# PURPOSE
# -------
# Decides whether a new OCR/extraction result should create a new
# workflow candidate, merge into an existing one, or be sent to
# review.
#
# WHY THIS EXISTS
# ---------------
# The Citadel app truncates titles, OCR misreads text, and multiple
# screenshots may describe the same workflow.
#
# Without a merge engine, the project would quickly create duplicate
# workflows such as:
#
#     White Scars Tactical Sq
#     White Scars Tactical Squad
#     White Scars Tactical Sqd
#
# This module prevents that bullshit.
#
# ============================================================


class WorkflowMergeEngine:
    def __init__(self):
        self.similarity = WorkflowSimilarity()

    def workflow_key(self, title):
        normalized = normalize_title(title)
        return normalized.replace(" ", "_").upper() or "UNKNOWN_WORKFLOW"

    def decide(self, raw_title, existing_rows):
        best = None
        best_score = 0

        for row in existing_rows:
            candidate_title = row.get("Best_Title", "")
            score = self.similarity.score(raw_title, candidate_title)

            if score > best_score:
                best = row
                best_score = score

        if best and best_score >= 90:
            return {
                "decision": "Merge",
                "matched_workflow_key": best["Workflow_Key"],
                "score": best_score,
                "reason": "Very high title similarity.",
            }

        if best and best_score >= 75:
            return {
                "decision": "Review Merge",
                "matched_workflow_key": best["Workflow_Key"],
                "score": best_score,
                "reason": "Possible duplicate; needs human review.",
            }

        return {
            "decision": "Create",
            "matched_workflow_key": "",
            "score": best_score,
            "reason": "No strong existing match found.",
        }
''',

    KNOWLEDGE_DIR / "workflow_metrics.py": r'''from pathlib import Path
import pandas as pd

from src.knowledge.knowledge_paths import KNOWLEDGE_DIR


# ============================================================
# WORKFLOW METRICS
# ============================================================
#
# PURPOSE
# -------
# Prints a quick dashboard for the knowledge acquisition engine.
#
# WHY THIS EXISTS
# ---------------
# As this project grows, Steve needs one command that answers:
#
#     How many workflows do we know about?
#     How many need review?
#     How many duplicates were prevented?
#     How healthy is the knowledge layer?
#
# ============================================================


FILES = {
    "Workflow State": KNOWLEDGE_DIR / "workflow_state.csv",
    "Workflow History": KNOWLEDGE_DIR / "workflow_history.csv",
    "Workflow Review": KNOWLEDGE_DIR / "workflow_review.csv",
    "Workflow Candidates": KNOWLEDGE_DIR / "workflow_candidates.csv",
}


def count_rows(path):
    if not path.exists():
        return 0

    return len(pd.read_csv(path).fillna(""))


def main():
    print("=" * 60)
    print("KNOWLEDGE ENGINE METRICS")
    print("=" * 60)

    for label, path in FILES.items():
        print(f"{label:<25} {count_rows(path)}")

    review_path = FILES["Workflow Review"]

    if review_path.exists():
        df = pd.read_csv(review_path).fillna("")
        if not df.empty and "Status" in df.columns:
            print("\nReview Status Counts")
            print("-" * 60)
            print(df["Status"].value_counts())

    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    KNOWLEDGE_DIR / "knowledge_manager.py": r'''from src.knowledge.workflow_catalog_builder import WorkflowCatalogBuilder
from src.knowledge.workflow_state import WorkflowState
from src.knowledge.workflow_history import WorkflowHistory
from src.knowledge.workflow_review import WorkflowReview
from src.knowledge.workflow_merge_engine import WorkflowMergeEngine


# ============================================================
# KNOWLEDGE MANAGER
# ============================================================
#
# PURPOSE
# -------
# Central coordinator for the knowledge acquisition system.
#
# WHY THIS EXISTS
# ---------------
# OCR extraction is messy. The system needs one place that decides:
#
#     Is this new?
#     Is this a duplicate?
#     Should it merge?
#     Should it go to review?
#     Should the known workflow state be updated?
#
# This manager connects the candidate catalog, workflow state,
# merge engine, history log, and review queue.
#
# ============================================================


class KnowledgeManager:
    def __init__(self):
        self.catalog_builder = WorkflowCatalogBuilder()
        self.state = WorkflowState()
        self.history = WorkflowHistory()
        self.review = WorkflowReview()
        self.merge_engine = WorkflowMergeEngine()

    def process_extraction_result(self, extraction_result):
        raw_title = extraction_result.get("raw_title", "")
        resolved_title = extraction_result.get("resolved_title", "")
        workflow_id = extraction_result.get("workflow_id", "")
        source_file = extraction_result.get("source_file", "")
        score = extraction_result.get("score", 0)
        reason = extraction_result.get("reason", "")

        existing_state = self.state.load()
        decision = self.merge_engine.decide(raw_title, existing_state)

        if decision["decision"] == "Merge":
            workflow_key = decision["matched_workflow_key"]

            updated = self.state.upsert(
                workflow_key=workflow_key,
                title=resolved_title or raw_title,
                workflow_id=workflow_id,
                source_file=source_file,
                confidence="High",
                status="Merged",
                notes=decision["reason"],
            )

            self.history.record(
                workflow_key=workflow_key,
                event_type="Merged Extraction",
                new_value=resolved_title or raw_title,
                source_file=source_file,
                notes=decision["reason"],
            )

            return {
                "action": "Merged",
                "workflow_key": workflow_key,
                "state": updated,
                "decision": decision,
            }

        if decision["decision"] == "Review Merge":
            workflow_key = decision["matched_workflow_key"]

            self.review.add(
                workflow_key=workflow_key,
                issue_type="Possible Duplicate",
                issue_detail=decision["reason"],
                source_file=source_file,
            )

            self.history.record(
                workflow_key=workflow_key,
                event_type="Merge Review Needed",
                new_value=raw_title,
                source_file=source_file,
                notes=decision["reason"],
            )

            return {
                "action": "Review Merge",
                "workflow_key": workflow_key,
                "decision": decision,
            }

        workflow_key = self.merge_engine.workflow_key(resolved_title or raw_title)

        candidate = self.catalog_builder.add_or_merge_candidate(
            raw_title=raw_title,
            resolved_title=resolved_title,
            workflow_id=workflow_id,
            source_file=source_file,
            resolver_score=score,
            reason=reason,
        )

        state_row = self.state.upsert(
            workflow_key=workflow_key,
            title=resolved_title or raw_title,
            workflow_id=workflow_id,
            source_file=source_file,
            confidence=candidate.get("confidence", "Very Low"),
            status=candidate.get("status", "Needs Review"),
            notes=reason,
        )

        self.history.record(
            workflow_key=workflow_key,
            event_type="Created Candidate",
            new_value=resolved_title or raw_title,
            source_file=source_file,
            notes=reason,
        )

        if candidate.get("status") in ["Manual Review", "Needs Quick Review"]:
            self.review.add(
                workflow_key=workflow_key,
                issue_type="Low Confidence Candidate",
                issue_detail=reason or "Candidate needs review before trusted import.",
                source_file=source_file,
            )

        return {
            "action": "Created",
            "workflow_key": workflow_key,
            "candidate": candidate,
            "state": state_row,
            "decision": decision,
        }
''',

    DEBUG_DIR / "knowledge_engine_v2_test.py": r'''from src.knowledge.knowledge_manager import KnowledgeManager


def main():
    print("=" * 60)
    print("KNOWLEDGE ENGINE V2 TEST")
    print("=" * 60)

    manager = KnowledgeManager()

    samples = [
        {
            "raw_title": "White Scars Tactical Sq",
            "resolved_title": "",
            "workflow_id": "UNRESOLVED_IMAGE0",
            "source_file": "archive/screenshots/image0.png",
            "score": 9,
            "reason": "Partial OCR title",
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
        print("\nPROCESSING:")
        print(sample["raw_title"])

        result = manager.process_extraction_result(sample)
        print(result)

    print("=" * 60)
    print("KNOWLEDGE ENGINE V2 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    SCRIPTS_DIR / "knowledge_engine_status.py": r'''from src.knowledge.workflow_metrics import main


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
    print("BUILDING KNOWLEDGE ENGINE V2")
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
    print("python -m src.debug.knowledge_engine_v2_test")
    print("python -m src.scripts.knowledge_engine_status")


if __name__ == "__main__":
    main()