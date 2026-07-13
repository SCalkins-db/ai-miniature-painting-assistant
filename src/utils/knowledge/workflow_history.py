from pathlib import Path
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
