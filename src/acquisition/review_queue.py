import csv
from datetime import datetime
from pathlib import Path


REVIEW_QUEUE_PATH = Path("review/review_queue.csv")


HEADERS = [
    "Created_At",
    "Source_File",
    "Workflow_ID",
    "Issue_Type",
    "Issue_Detail",
    "Status",
]


class ReviewQueue:
    def __init__(self, queue_path=REVIEW_QUEUE_PATH):
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_queue()

    def _ensure_queue(self):
        if self.queue_path.exists():
            return

        with self.queue_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()

    def add(self, source_file, issue_type, issue_detail, workflow_id=""):
        with self.queue_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "Created_At": datetime.now().isoformat(timespec="seconds"),
                "Source_File": str(source_file),
                "Workflow_ID": workflow_id,
                "Issue_Type": issue_type,
                "Issue_Detail": issue_detail,
                "Status": "Open",
            })
