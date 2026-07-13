import csv
from datetime import datetime
from pathlib import Path

from src.acquisition.hashing import file_sha256


IMPORT_LOG_PATH = Path("data/imports/import_log.csv")


HEADERS = [
    "File_Hash",
    "File_Name",
    "File_Path",
    "File_Type",
    "Import_Date",
    "Status",
    "Workflow_ID",
    "Notes",
]


class ImportLog:
    def __init__(self, log_path=IMPORT_LOG_PATH):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_log()

    def _ensure_log(self):
        if self.log_path.exists():
            return

        with self.log_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()

    def load_hashes(self):
        hashes = set()

        with self.log_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                hashes.add(row["File_Hash"])

        return hashes

    def already_imported(self, file_path):
        file_hash = file_sha256(file_path)
        return file_hash in self.load_hashes()

    def record(self, file_path, file_type, status, workflow_id="", notes=""):
        file_path = Path(file_path)
        file_hash = file_sha256(file_path)

        with self.log_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "File_Hash": file_hash,
                "File_Name": file_path.name,
                "File_Path": str(file_path),
                "File_Type": file_type,
                "Import_Date": datetime.now().isoformat(timespec="seconds"),
                "Status": status,
                "Workflow_ID": workflow_id,
                "Notes": notes,
            })
