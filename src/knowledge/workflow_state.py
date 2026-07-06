from pathlib import Path
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
